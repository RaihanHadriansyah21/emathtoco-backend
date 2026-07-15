from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from redis import Redis
from rq import Queue, Retry
from rq.job import Job
from rq.serializers import JSONSerializer
from rq.worker import Worker

from config import get_settings
from domain import AIModel
from utils.logging_helper import logger
from utils.supabase_client import get_service_client

QUEUE_NAME = "ai"
LOCK_PREFIX = "ai-lock:"
RECONCILE_LOCK_KEY = "ai-reconcile-stale-lock"
ACTIVE_RQ_STATUSES = {"queued", "deferred", "scheduled", "started"}


@dataclass(frozen=True)
class EnqueueResult:
    job_id: str | None
    accepted_ids: list[str]
    rejected: dict[str, str]


def get_redis() -> Redis:
    return Redis.from_url(
        get_settings().redis_url,
        decode_responses=False,
        health_check_interval=30,
        socket_connect_timeout=3,
        socket_timeout=5,
    )


def get_queue(connection: Redis | None = None) -> Queue:
    return Queue(
        QUEUE_NAME,
        connection=connection or get_redis(),
        serializer=JSONSerializer,
        default_timeout=get_settings().rq_job_timeout,
    )


def _lock_key(submission_id: str) -> str:
    return f"{LOCK_PREFIX}{submission_id}"


def _normalize_rq_status(raw_status: object) -> str:
    raw_status_value = getattr(raw_status, "value", raw_status)
    return str(raw_status_value).lower()


def _decode_lock_owner(raw_owner: object) -> str | None:
    if raw_owner is None:
        return None
    if isinstance(raw_owner, bytes):
        return raw_owner.decode("utf-8", errors="replace")
    return str(raw_owner)


def _is_job_still_active(connection: Redis, job_id: str) -> bool:
    try:
        job = Job.fetch(job_id, connection=connection, serializer=JSONSerializer)
        return _normalize_rq_status(job.get_status(refresh=True)) in ACTIVE_RQ_STATUSES
    except Exception:
        logger.warning(
            "AI lock owner job is missing or unreadable; treating lock as stale",
            extra={"job_id": job_id},
        )
        return False


def _acquire_lock(connection: Redis, submission_id: str, job_id: str) -> bool:
    ttl = get_settings().rq_job_timeout * 2 + 180
    key = _lock_key(submission_id)
    if connection.set(key, job_id, ex=ttl, nx=True):
        return True

    existing_owner = _decode_lock_owner(connection.get(key))
    if existing_owner and _is_job_still_active(connection, existing_owner):
        return False

    if existing_owner:
        _release_lock(connection, submission_id, existing_owner)
    return bool(connection.set(key, job_id, ex=ttl, nx=True))


def _release_lock(connection: Redis, submission_id: str, job_id: str) -> None:
    script = """
    if redis.call('get', KEYS[1]) == ARGV[1] then
      return redis.call('del', KEYS[1])
    end
    return 0
    """
    connection.eval(script, 1, _lock_key(submission_id), job_id)


def _claim_submission(submission_id: str, model: AIModel) -> dict:
    response = (
        get_service_client()
        .rpc(
            "claim_ai_job",
            {
                "p_submission_id": submission_id,
                "p_model_ai": model.value,
            },
        )
        .execute()
    )
    return response.data or {"claimed": False, "reason": "claim_failed"}


def _release_claim(submission_id: str, claim: dict) -> None:
    get_service_client().rpc(
        "release_ai_job",
        {
            "p_submission_id": submission_id,
            "p_previous_status_submit": claim["previous_status_submit"],
            "p_previous_ai_status": claim["previous_ai_status"],
        },
    ).execute()


def reconcile_stale_ai_jobs(connection: Redis | None = None) -> int:
    redis_connection = connection or get_redis()
    if not redis_connection.set(RECONCILE_LOCK_KEY, b"1", ex=60, nx=True):
        return 0
    stale_before = datetime.now(UTC) - timedelta(
        seconds=get_settings().rq_job_timeout + 300,
    )
    response = get_service_client().rpc(
        "reconcile_stale_ai_jobs",
        {"p_stale_before": stale_before.isoformat()},
    ).execute()
    reconciled = response.data if isinstance(response.data, list) else []
    if reconciled:
        logger.warning(
            "Reconciled stale AI processing states",
            extra={"count": len(reconciled)},
        )
    return len(reconciled)


def enqueue_predictions(
    submission_ids: list[UUID],
    model: AIModel,
) -> EnqueueResult:
    connection = get_redis()
    connection.ping()
    reconcile_stale_ai_jobs(connection)
    queue = get_queue(connection)
    job_id = str(uuid4())
    accepted: list[str] = []
    rejected: dict[str, str] = {}
    claims: dict[str, dict] = {}

    for raw_id in submission_ids:
        submission_id = str(raw_id)
        if not _acquire_lock(connection, submission_id, job_id):
            rejected[submission_id] = "already_queued"
            continue

        try:
            claim = _claim_submission(submission_id, model)
        except Exception:
            _release_lock(connection, submission_id, job_id)
            rejected[submission_id] = "claim_unavailable"
            logger.exception("AI job claim failed")
            continue

        if not claim.get("claimed"):
            _release_lock(connection, submission_id, job_id)
            rejected[submission_id] = str(claim.get("reason", "not_eligible"))
            continue

        claims[submission_id] = claim
        accepted.append(submission_id)

    if not accepted:
        return EnqueueResult(job_id=None, accepted_ids=[], rejected=rejected)

    try:
        job = queue.enqueue(
            "services.tasks.process_batch_job",
            accepted,
            model.value,
            job_id,
            job_id=job_id,
            retry=Retry(max=1, interval=[30]),
            job_timeout=get_settings().rq_job_timeout,
            result_ttl=86400,
            failure_ttl=604800,
            meta={
                "accepted_ids": accepted,
                "rejected": rejected,
                "progress": 0,
                "safe_error_code": None,
            },
        )
        job.save_meta()
    except Exception:
        for submission_id in accepted:
            try:
                _release_claim(submission_id, claims[submission_id])
            finally:
                _release_lock(connection, submission_id, job_id)
        logger.exception("Failed to enqueue AI job")
        raise

    return EnqueueResult(
        job_id=job.id,
        accepted_ids=accepted,
        rejected=rejected,
    )


def get_job_status(job_id: str) -> dict:
    connection = get_redis()
    try:
        job = Job.fetch(job_id, connection=connection, serializer=JSONSerializer)
    except Exception as exc:
        raise KeyError(job_id) from exc

    normalized_status = _normalize_rq_status(job.get_status(refresh=True))
    status_map = {
        "queued": "queued",
        "deferred": "queued",
        "scheduled": "queued",
        "started": "started",
        "finished": "completed",
        "failed": "failed",
        "stopped": "failed",
        "canceled": "failed",
    }
    status = status_map.get(normalized_status, "queued")
    result: dict = {}
    if status == "completed":
        try:
            raw_result = job.return_value(refresh=True)
            if isinstance(raw_result, dict):
                result = raw_result
        except Exception:
            logger.exception("Failed to read completed AI job result")

    return {
        "job_id": job.id,
        "status": status,
        "progress": int(job.meta.get("progress", 0)),
        "accepted_ids": job.meta.get("accepted_ids", []),
        "rejected": job.meta.get("rejected", {}),
        "error_code": job.meta.get("safe_error_code"),
        "completed_ids": result.get("completed_ids", []),
        "failed": result.get("failed", {}),
    }


def enqueue_storage_cleanup(object_paths: list[str]) -> str | None:
    normalized_paths = sorted(
        {
            path
            for path in object_paths
            if isinstance(path, str) and path and len(path) <= 2048
        }
    )
    if not normalized_paths:
        return None

    queue = get_queue()
    job = queue.enqueue(
        "services.tasks.cleanup_storage_objects",
        normalized_paths,
        job_id=str(uuid4()),
        retry=Retry(max=3, interval=[30, 120, 300]),
        job_timeout=300,
        result_ttl=86400,
        failure_ttl=604800,
    )
    return job.id


def queue_readiness() -> dict[str, bool]:
    connection = get_redis()
    redis_ready = bool(connection.ping())
    workers = Worker.all(connection=connection)
    now = datetime.now(UTC)

    def is_fresh(worker: Worker) -> bool:
        raw_state = getattr(worker.state, "value", worker.state)
        if str(raw_state).lower() not in {"busy", "idle"}:
            return False

        last_heartbeat = worker.last_heartbeat
        if last_heartbeat is None:
            return False
        if last_heartbeat.tzinfo is None:
            last_heartbeat = last_heartbeat.replace(tzinfo=UTC)

        worker_ttl = int(getattr(worker, "worker_ttl", 0) or 420)
        freshness_window = timedelta(seconds=max(worker_ttl, 60))
        return now - last_heartbeat <= freshness_window

    worker_ready = any(is_fresh(worker) for worker in workers)
    return {"redis": redis_ready, "worker": worker_ready}


def release_job_lock(submission_id: str, job_id: str) -> None:
    _release_lock(get_redis(), submission_id, job_id)
