import numpy as np

from repositories.lembar_jawaban_repository import get_answer_sheets
from repositories.prediction_repository import upsert_prediction
from repositories.submission_repository import (
    get_submission_by_id,
    update_ai_status,
    update_submission_result,
)
from services.class_mapping import get_score
from services.image_service import download_image
from services.model_registry import get_model, MODEL_CONFIG
from services.preprocess import preprocess_image

# Nama arsitektur default yang digunakan pada tahap ini
MODEL_AI = "MobileNetV2"


def process_single_sheet(sheet: dict, model_name: str = "MobileNetV2") -> dict:
    """
    Proses satu lembar jawaban: download → preprocess → predict → save.

    Parameter:
        sheet : dict satu record dari tabel lembar_jawaban
                Harus memiliki key:
                  - id
                  - pengumpulan_tugas_id
                  - section_code
                  - image_url
        model_name : nama model yang dipilih, contoh "MobileNetV2", "DenseNet201", "InceptionV3"

    Return:
        dict hasil prediksi:
          {
            "section_code"    : str,
            "predicted_class" : int,
            "predicted_score" : int,
            "confidence"      : float,
            "status"          : "success"
          }

    Raise:
        ValueError      jika image gagal di-decode (None dari OpenCV)
        Exception lain  jika ada error di download / predict / save
    """
    section_code = sheet["section_code"]
    image_url = sheet["image_url"]
    lembar_jawaban_id = sheet["id"]
    pengumpulan_tugas_id = sheet["pengumpulan_tugas_id"]

    # --------------------------------------------------
    # 1. Download + decode image
    # --------------------------------------------------
    img = download_image(image_url)
    if img is None:
        raise ValueError(
            f"Gagal decode image untuk section {section_code} (path: {image_url})"
        )

    # --------------------------------------------------
    # 2. Normalize and check model settings
    # --------------------------------------------------
    normalized_model_name = model_name
    if not model_name:
        normalized_model_name = "MobileNetV2"
    elif model_name.lower() == "mobilenetv2":
        normalized_model_name = "MobileNetV2"
    elif model_name.lower() == "densenet201":
        normalized_model_name = "DenseNet201"
    elif model_name.lower() == "inceptionv3":
        normalized_model_name = "InceptionV3"

    if normalized_model_name not in MODEL_CONFIG:
        normalized_model_name = "MobileNetV2"

    input_size = MODEL_CONFIG[normalized_model_name]["input_size"]

    # --------------------------------------------------
    # 3. Preprocess → (1, H, W, 3) float32
    # --------------------------------------------------
    processed = preprocess_image(img, input_size)

    # --------------------------------------------------
    # 4. Lazy load model dari cache
    # --------------------------------------------------
    model = get_model(section_code, normalized_model_name)

    # --------------------------------------------------
    # 5. Predict
    # --------------------------------------------------
    output = model.predict(processed, verbose=0)
    predicted_class = int(np.argmax(output[0]))
    confidence = float(np.max(output[0]))

    # --------------------------------------------------
    # 6. Convert class → score via CLASS_SCORE_MAP
    # --------------------------------------------------
    predicted_score = get_score(section_code, predicted_class)

    # --------------------------------------------------
    # 7. Simpan ke tabel hasil_prediksi (upsert)
    # --------------------------------------------------
    upsert_prediction(
        pengumpulan_tugas_id=pengumpulan_tugas_id,
        lembar_jawaban_id=lembar_jawaban_id,
        section_code=section_code,
        model_ai=normalized_model_name,
        predicted_class=predicted_class,
        predicted_score=predicted_score,
        confidence=confidence,
        status="success",
    )

    return {
        "section_code": section_code,
        "predicted_class": predicted_class,
        "predicted_score": predicted_score,
        "confidence": round(confidence, 4),
        "status": "success",
    }


def process_submission(submission_id: str, model_name: str = "MobileNetV2") -> dict:
    """
    Pipeline lengkap untuk satu submission.
    """
    warnings = []

    # --------------------------------------------------
    # 1. Validasi submission
    # --------------------------------------------------
    submission = get_submission_by_id(submission_id)
    if not submission:
        return {
            "success": False,
            "error": f"Submission '{submission_id}' tidak ditemukan di database.",
        }

    # Normalize model_name
    normalized_model_name = model_name
    if not model_name:
        normalized_model_name = "MobileNetV2"
    elif model_name.lower() == "mobilenetv2":
        normalized_model_name = "MobileNetV2"
    elif model_name.lower() == "densenet201":
        normalized_model_name = "DenseNet201"
    elif model_name.lower() == "inceptionv3":
        normalized_model_name = "InceptionV3"

    if normalized_model_name not in MODEL_CONFIG:
        normalized_model_name = "MobileNetV2"

    # --------------------------------------------------
    # 2. Update status → processing
    # --------------------------------------------------
    try:
        update_ai_status(submission_id, "processing")
    except Exception as e:
        warnings.append(f"update_ai_status gagal (kolom mungkin belum ada): {e}")

    # --------------------------------------------------
    # 3. Ambil semua lembar jawaban
    # --------------------------------------------------
    sheets = get_answer_sheets(submission_id)
    if not sheets:
        try:
            update_ai_status(submission_id, "failed")
        except Exception:
            pass
        return {
            "success": False,
            "error": "Tidak ada lembar jawaban untuk submission ini.",
        }

    results = []
    errors = []

    # --------------------------------------------------
    # 4. Proses setiap sheet
    # --------------------------------------------------
    for sheet in sheets:
        section_code = sheet.get("section_code", "unknown")
        try:
            result = process_single_sheet(sheet, model_name=normalized_model_name)
            results.append(result)
        except Exception as e:
            errors.append(
                {
                    "section_code": section_code,
                    "error": str(e),
                }
            )

    # --------------------------------------------------
    # 5. Hitung nilai_akhir
    # --------------------------------------------------
    nilai_akhir = sum(r["predicted_score"] for r in results)

    # --------------------------------------------------
    # 6. Tentukan status akhir
    # --------------------------------------------------
    if len(errors) == 0:
        ai_status = "completed"
    elif len(results) > 0:
        ai_status = "partial"
    else:
        ai_status = "failed"

    # --------------------------------------------------
    # 7. Update submission
    # --------------------------------------------------
    try:
        update_submission_result(
            submission_id=submission_id,
            nilai_akhir=nilai_akhir,
            ai_status=ai_status,
            model_ai=normalized_model_name,
        )
    except Exception as e:
        warnings.append(
            f"update_submission_result gagal: {e}. "
            "Pastikan kolom ai_status dan ai_processed_at sudah ada di tabel "
            "pengumpulan_tugas."
        )
        try:
            from utils.supabase_client import supabase

            supabase.table("pengumpulan_tugas").update({
                "nilai_akhir": nilai_akhir,
                "model_ai": normalized_model_name
            }).eq(
                "id", submission_id
            ).execute()
        except Exception as fallback_err:
            warnings.append(f"Fallback update nilai_akhir/model_ai juga gagal: {fallback_err}")

    return {
        "success": ai_status in ("completed", "partial"),
        "submission_id": submission_id,
        "total_sheets": len(sheets),
        "processed": len(results),
        "failed": len(errors),
        "nilai_akhir": nilai_akhir,
        "ai_status": ai_status,
        "model_ai": normalized_model_name,
        "results": results,
        "errors": errors,
        "warnings": warnings,
    }
