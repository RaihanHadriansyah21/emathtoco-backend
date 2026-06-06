from datetime import datetime, timezone

from utils.supabase_client import supabase


def get_submission_by_id(submission_id: str) -> dict | None:
    """
    Ambil satu record pengumpulan_tugas berdasarkan ID.

    Return:
        dict record jika ditemukan
        None jika tidak ada
    """
    response = (
        supabase.table("pengumpulan_tugas")
        .select("*")
        .eq("id", submission_id)
        .maybe_single()
        .execute()
    )
    return response.data


def update_submission_result(
    submission_id: str,
    nilai_akhir: float,
    ai_status: str,
    model_ai: str = None,
) -> list:
    """
    Update hasil akhir submission setelah AI selesai memproses.

    Kolom yang diupdate:
        nilai_akhir      : total score dari semua section
        ai_status        : "completed" | "partial" | "failed"
        status_submit    : "submitted" if completed else "failed"
        ai_processed_at  : timestamp sekarang (UTC)
        model_ai         : nama model yang digunakan (jika ada)
    """
    payload = {
        "nilai_akhir": nilai_akhir,
        "ai_status": ai_status,
        "status_submit": "submitted" if ai_status == "completed" else "failed",
        "ai_processed_at": datetime.now(timezone.utc).isoformat(),
    }
    if model_ai is not None:
        payload["model_ai"] = model_ai

    response = (
        supabase.table("pengumpulan_tugas")
        .update(payload)
        .eq("id", submission_id)
        .execute()
    )
    return response.data


def update_ai_status(submission_id: str, status: str) -> list:
    """
    Update ai_status submission.

    Digunakan untuk menandai:
        "processing" → saat AI mulai berjalan
        "completed"  → saat semua section berhasil
        "partial"    → saat sebagian section gagal
        "failed"     → saat semua section gagal
    """
    payload = {"ai_status": status}
    if status == "failed":
        payload["status_submit"] = "failed"
    elif status == "processing":
        payload["status_submit"] = "processing_ai"
    elif status == "completed":
        payload["status_submit"] = "submitted"

    response = (
        supabase.table("pengumpulan_tugas")
        .update(payload)
        .eq("id", submission_id)
        .execute()
    )
    return response.data
