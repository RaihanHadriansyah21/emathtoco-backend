from types import SimpleNamespace
from uuid import UUID

import pytest
from rq.job import JobStatus

from domain import AIModel
from services import queue_service


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def ping(self) -> bool:
        return True

    def set(
        self,
        key: str,
        value: str,
        *,
        ex: int,
        nx: bool,
    ) -> bool:
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True


class FakeJob:
    def __init__(self, job_id: str) -> None:
        self.id = job_id

    def save_meta(self) -> None:
        return None


class FakeQueue:
    def enqueue(self, *args, **kwargs) -> FakeJob:
        return FakeJob(kwargs["job_id"])


def configure_queue_mocks(monkeypatch: pytest.MonkeyPatch, redis: FakeRedis) -> None:
    monkeypatch.setattr(queue_service, "get_redis", lambda: redis)
    monkeypatch.setattr(queue_service, "get_queue", lambda connection: FakeQueue())
    monkeypatch.setattr(
        queue_service,
        "get_settings",
        lambda: SimpleNamespace(rq_job_timeout=1800),
    )
    monkeypatch.setattr(queue_service, "reconcile_stale_ai_jobs", lambda connection: 0)
    monkeypatch.setattr(
        queue_service,
        "_claim_submission",
        lambda submission_id, model: {
            "claimed": True,
            "previous_status_submit": "submitted",
            "previous_ai_status": "pending",
        },
    )


def test_duplicate_ai_request_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    redis = FakeRedis()
    configure_queue_mocks(monkeypatch, redis)
    submission_id = UUID("50000000-0000-0000-0000-000000000001")

    first = queue_service.enqueue_predictions(
        [submission_id],
        AIModel.MOBILENET_V2,
    )
    second = queue_service.enqueue_predictions(
        [submission_id],
        AIModel.MOBILENET_V2,
    )

    assert first.accepted_ids == [str(submission_id)]
    assert second.accepted_ids == []
    assert second.rejected[str(submission_id)] == "already_queued"


def test_enqueue_failure_restores_claim_and_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis = FakeRedis()
    configure_queue_mocks(monkeypatch, redis)
    submission_id = UUID("50000000-0000-0000-0000-000000000001")
    released_claims: list[str] = []
    released_locks: list[str] = []

    class FailingQueue:
        def enqueue(self, *args, **kwargs):
            raise RuntimeError("queue unavailable")

    monkeypatch.setattr(
        queue_service,
        "get_queue",
        lambda connection: FailingQueue(),
    )
    monkeypatch.setattr(
        queue_service,
        "_release_claim",
        lambda submission, claim: released_claims.append(submission),
    )
    monkeypatch.setattr(
        queue_service,
        "_release_lock",
        lambda connection, submission, owner: released_locks.append(submission),
    )

    with pytest.raises(RuntimeError, match="queue unavailable"):
        queue_service.enqueue_predictions(
            [submission_id],
            AIModel.MOBILENET_V2,
        )

    assert released_claims == [str(submission_id)]
    assert released_locks == [str(submission_id)]


def test_finished_rq_enum_is_reported_as_completed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submission_id = "50000000-0000-0000-0000-000000000001"

    class CompletedJob:
        id = "60000000-0000-0000-0000-000000000001"
        meta = {
            "progress": 100,
            "accepted_ids": [submission_id],
            "rejected": {},
            "safe_error_code": None,
        }

        def get_status(self, *, refresh: bool):
            assert refresh is True
            return JobStatus.FINISHED

        def return_value(self, *, refresh: bool):
            assert refresh is True
            return {
                "completed_ids": [submission_id],
                "failed": {},
            }

    monkeypatch.setattr(queue_service, "get_redis", lambda: FakeRedis())
    monkeypatch.setattr(
        queue_service.Job,
        "fetch",
        lambda *args, **kwargs: CompletedJob(),
    )

    status = queue_service.get_job_status(CompletedJob.id)

    assert status["status"] == "completed"
    assert status["completed_ids"] == [submission_id]
    assert status["failed"] == {}
