from utils.supabase_client import supabase


def upsert_prediction(
    pengumpulan_tugas_id: str,
    lembar_jawaban_id: str,
    section_code: str,
    model_ai: str,
    predicted_class: int,
    predicted_score: int,
    confidence: float,
    status: str = "success",
    error_message: str = None,
) -> list:
    """
    UPSERT satu record ke tabel hasil_prediksi.

    Aman untuk re-run: jika kombinasi
    (pengumpulan_tugas_id, section_code) sudah ada,
    record akan di-UPDATE bukan INSERT duplikat.
    Ini memastikan hanya ada SATU hasil per section per submission,
    bahkan jika dosen mengganti model AI.

    Prasyarat di database:
        ALTER TABLE hasil_prediksi
            ADD CONSTRAINT uq_hasil_prediksi_submission_section
            UNIQUE (pengumpulan_tugas_id, section_code);
    """
    data = {
        "pengumpulan_tugas_id": pengumpulan_tugas_id,
        "lembar_jawaban_id": lembar_jawaban_id,
        "section_code": section_code,
        "model_ai": model_ai,
        "predicted_class": int(predicted_class),
        "predicted_score": int(predicted_score),
        "confidence": float(confidence),
        "status": status,
        "error_message": error_message,
    }
    response = (
        supabase.table("hasil_prediksi")
        .upsert(data, on_conflict="pengumpulan_tugas_id,section_code")
        .execute()
    )
    return response.data


def get_predictions_by_submission(submission_id: str, model_ai: str = None) -> list:
    """
    Ambil semua hasil prediksi untuk satu submission_id, optionally filtered by model_ai.
    """
    query = (
        supabase.table("hasil_prediksi")
        .select("section_code, predicted_class, predicted_score, confidence, model_ai")
        .eq("pengumpulan_tugas_id", submission_id)
    )
    if model_ai:
        if model_ai.lower() == "mobilenetv2":
            query = query.in_("model_ai", ["MobileNetV2", "MobilenetV2"])
        else:
            query = query.eq("model_ai", model_ai)
    response = query.execute()
    return response.data


def delete_predictions_by_submission(submission_id: str, model_ai: str = None) -> list:
    """
    Hapus SEMUA hasil prediksi untuk satu submission_id.

    Parameter model_ai tetap diterima untuk kompatibilitas mundur,
    tetapi diabaikan — selalu menghapus semua prediksi untuk
    submission agar tidak ada data lama menumpuk saat re-run.
    """
    query = supabase.table("hasil_prediksi").delete().eq("pengumpulan_tugas_id", submission_id)
    response = query.execute()
    return response.data

