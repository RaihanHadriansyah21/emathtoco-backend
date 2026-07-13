from __future__ import annotations

import os
import socket
from uuid import uuid4

from rq import Queue, Worker
from rq.serializers import JSONSerializer

from config import get_settings
from services.model_manifest import validate_model_manifest
from services.queue_service import QUEUE_NAME, get_redis, reconcile_stale_ai_jobs
from utils.logging_helper import logger


def main() -> None:
    settings = get_settings()
    os.environ.setdefault("TF_NUM_INTRAOP_THREADS", "6")
    os.environ.setdefault("TF_NUM_INTEROP_THREADS", "2")
    os.environ.setdefault("OMP_NUM_THREADS", "6")

    validate_model_manifest(settings.model_root)
    connection = get_redis()
    connection.ping()
    reconcile_stale_ai_jobs(connection)
    queue = Queue(
        QUEUE_NAME,
        connection=connection,
        serializer=JSONSerializer,
        default_timeout=settings.rq_job_timeout,
    )
    logger.info("AI worker readiness checks passed")
    worker = Worker(
        [queue],
        connection=connection,
        serializer=JSONSerializer,
        worker_ttl=90,
        # A Docker/host restart can interrupt RQ before it unregisters the
        # previous worker. A process-unique name prevents that stale key from
        # blocking the replacement worker until Redis expires it.
        name=(
            os.getenv("RQ_WORKER_NAME")
            or f"emathtoco-ai-worker-{socket.gethostname()}-{uuid4().hex[:12]}"
        ),
    )
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
