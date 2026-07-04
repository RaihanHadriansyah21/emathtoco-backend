from __future__ import annotations

from collections import defaultdict

from rq import get_current_job

from domain import SECTION_CODES
from repositories.lembar_jawaban_repository import get_answer_sheets
from repositories.prediction_repository import delete_predictions_by_submission
from services.image_service import check_file_exists
from utils.logging_helper import logger
from utils.supabase_client import get_service_client


def cleanup_storage_objects(object_paths: list[str]) -> dict:
    client = get_service_client()
    removed = 0
    for offset in range(0, len(object_paths), 100):
        chunk = object_paths[offset : offset + 100]
        # Supabase Storage remove is idempotent for paths that are already gone.
        client.storage.from_("lembar-jawaban").remove(chunk)
        removed += len(chunk)
    return {"removed": removed}


def _mark_failed(submission_id: str, error_code: str) -> None:
    get_service_client().rpc(
        "fail_ai_job",
        {
            "p_submission_id": submission_id,
            "p_error_code": error_code,
        },
    ).execute()


def _mark_completed(submission_id: str, total_score: float) -> None:
    response = get_service_client().rpc(
        "complete_ai_job",
        {
            "p_submission_id": submission_id,
            "p_total_score": total_score,
        },
    ).execute()
    if response.data is not True:
        raise RuntimeError("ai_completion_state_conflict")


def _release_locks(submission_ids: list[str], job_id: str) -> None:
    from services.queue_service import release_job_lock

    for submission_id in submission_ids:
        try:
            release_job_lock(submission_id, job_id)
        except Exception:
            logger.exception("Failed to release AI lock")


def process_batch_job(
    submission_ids: list[str],
    model_name: str,
    lock_owner: str,
) -> dict:
    # TensorFlow and model modules are imported only inside the worker process.
    from services.prediction_service import process_single_sheet

    job = get_current_job()
    if job is None:
        raise RuntimeError("rq_job_context_required")

    completed_successfully = False
    terminal_failure = False
    try:
        sheet_maps: dict[str, dict[str, dict]] = {}
        scores: dict[str, int] = defaultdict(int)
        # Preserve the accepted request order. Each section is processed for
        # submissions in this order before the worker advances to the next
        # section model.
        active_ids: list[str] = list(submission_ids)
        failed_ids: dict[str, str] = {}

        for submission_id in submission_ids:
            sheets = get_answer_sheets(submission_id)
            by_section = {sheet["section_code"]: sheet for sheet in sheets}
            if set(by_section) != set(SECTION_CODES):
                failed_ids[submission_id] = "INCOMPLETE_SECTIONS"
                active_ids.remove(submission_id)
                _mark_failed(submission_id, "INCOMPLETE_SECTIONS")
                continue
            if any(not check_file_exists(sheet["image_url"]) for sheet in sheets):
                failed_ids[submission_id] = "MISSING_IMAGE_OBJECT"
                active_ids.remove(submission_id)
                _mark_failed(submission_id, "MISSING_IMAGE_OBJECT")
                continue
            delete_predictions_by_submission(submission_id)
            sheet_maps[submission_id] = by_section

        total_steps = max(len(active_ids) * len(SECTION_CODES), 1)
        completed_steps = 0

        # Section-first iteration keeps one section model hot while processing
        # every submission before moving to the next model artifact.
        for section in SECTION_CODES:
            for submission_id in tuple(active_ids):
                try:
                    result = process_single_sheet(
                        sheet_maps[submission_id][section],
                        model_name=model_name,
                    )
                    scores[submission_id] += int(result["predicted_score"])
                except Exception:
                    logger.exception("AI section processing failed")
                    delete_predictions_by_submission(submission_id)
                    _mark_failed(submission_id, "SECTION_INFERENCE_FAILED")
                    failed_ids[submission_id] = "SECTION_INFERENCE_FAILED"
                    active_ids.remove(submission_id)
                finally:
                    completed_steps += 1
                    job.meta["progress"] = min(
                        99,
                        int(completed_steps / total_steps * 100),
                    )
                    job.save_meta()

        for submission_id in active_ids:
            _mark_completed(submission_id, float(scores[submission_id]))

        job.meta["progress"] = 100
        job.meta["safe_error_code"] = None
        job.save_meta()
        completed_successfully = True
        return {
            "completed_ids": list(active_ids),
            "failed": failed_ids,
        }
    except Exception:
        retries_left = int(getattr(job, "retries_left", 0) or 0)
        terminal_failure = retries_left <= 0
        if terminal_failure:
            for submission_id in submission_ids:
                try:
                    _mark_failed(submission_id, "AI_JOB_FAILED")
                except Exception:
                    logger.exception("Failed to persist terminal AI failure")
            job.meta["safe_error_code"] = "AI_JOB_FAILED"
            job.save_meta()
        raise
    finally:
        if completed_successfully or terminal_failure:
            _release_locks(submission_ids, lock_owner)
        elif int(getattr(job, "retries_left", 0) or 0) > 0:
            # Keep locks across the scheduled retry.
            pass
        else:
            _release_locks(submission_ids, lock_owner)
