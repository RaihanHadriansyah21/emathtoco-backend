import numpy as np
from datetime import datetime

from repositories.lembar_jawaban_repository import get_answer_sheets
from repositories.prediction_repository import upsert_prediction, delete_predictions_by_submission
from repositories.submission_repository import (
    get_submission_by_id,
    update_ai_status,
    update_submission_result,
)
from services.class_mapping import get_score
from services.image_service import download_image, check_file_exists
from services.model_registry import get_model, MODEL_CONFIG
from services.preprocess import preprocess_image
from services.settings_service import settings_service
from utils.logging_helper import logger

# Nama arsitektur default yang digunakan pada tahap ini
MODEL_AI = "MobileNetV2"


def _normalize_model_name(model_name: str) -> str:
    """Normalize model name ke format standar."""
    if not model_name or model_name.lower() in ["", "none", "null"]:
        model_name = settings_service.get_setting("active_model")
        
    if not model_name:
        model_name = "MobileNetV2"
        
    lower = model_name.lower()
    if lower == "mobilenetv2":
        return "MobileNetV2"
    elif lower == "densenet121":
        return "DenseNet121"
    elif lower == "inceptionv3":
        return "InceptionV3"
    return model_name if model_name in MODEL_CONFIG else "MobileNetV2"


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
        model_name : nama model yang dipilih, contoh "MobileNetV2", "DenseNet121", "InceptionV3"

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
        FileNotFoundError  jika file tidak ditemukan di Storage
        ValueError         jika image gagal di-decode (None dari OpenCV)
        Exception lain     jika ada error di download / predict / save
    """
    section_code = sheet["section_code"]
    image_url = sheet["image_url"]
    lembar_jawaban_id = sheet["id"]
    pengumpulan_tugas_id = sheet["pengumpulan_tugas_id"]

    normalized_model_name = _normalize_model_name(model_name)

    verbose = settings_service.get_setting("verbose_logging") == "true"
    if verbose:
        logger.info(f"[AI VERBOSE] [process_single_sheet] Starting section {section_code} with model {normalized_model_name} (path: {image_url})")

    # --------------------------------------------------
    # 1. Download + decode image
    # --------------------------------------------------
    img = download_image(image_url)
    if img is None:
        raise ValueError(
            f"Gagal decode image untuk section {section_code} (path: {image_url})"
        )

    if verbose:
        logger.info(f"[AI VERBOSE] [process_single_sheet] Image downloaded successfully, size: {img.shape}")

    input_size = MODEL_CONFIG[normalized_model_name]["input_size"]

    # --------------------------------------------------
    # 2. Preprocess → (1, H, W, 3) float32
    # --------------------------------------------------
    processed = preprocess_image(img, input_size)

    # --------------------------------------------------
    # 3. Lazy load model dari cache
    # --------------------------------------------------
    model = get_model(section_code, normalized_model_name)

    # --------------------------------------------------
    # 4. Predict
    # --------------------------------------------------
    output = model.predict(processed, verbose=0)
    predicted_class = int(np.argmax(output[0]))
    confidence = float(np.max(output[0]))

    if verbose:
        logger.info(f"[AI VERBOSE] [process_single_sheet] Section {section_code} prediction raw output shape: {output.shape}, class: {predicted_class}, confidence: {confidence:.4f}")

    # --------------------------------------------------
    # 5. Convert class → score via CLASS_SCORE_MAP
    # --------------------------------------------------
    predicted_score = get_score(section_code, predicted_class)

    if verbose:
        logger.info(f"[AI VERBOSE] [process_single_sheet] Section {section_code} mapped score: {predicted_score}")

    # --------------------------------------------------
    # 6. Simpan ke tabel hasil_prediksi (upsert)
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


def _validate_storage_files(sheets: list) -> tuple[list, list]:
    """
    Pre-flight check: validasi bahwa file gambar benar-benar ada di Storage
    untuk setiap lembar jawaban.

    Return:
        (available_sheets, missing_sheets)
        available_sheets : list of sheets yang file-nya ada
        missing_sheets   : list of dicts {section_code, image_url} yang file-nya hilang
    """
    available = []
    missing = []

    for sheet in sheets:
        section_code = sheet.get("section_code", "unknown")
        image_url = sheet.get("image_url", "")

        if not image_url:
            logger.warning(f"[AI] Missing file: submission={sheet.get('pengumpulan_tugas_id')} "
                           f"section={section_code} path=(empty)")
            missing.append({
                "section_code": section_code,
                "image_url": "(empty)",
                "reason": "image_url kosong di database",
            })
            continue

        if check_file_exists(image_url):
            available.append(sheet)
        else:
            logger.warning(f"[AI] Missing file: submission={sheet.get('pengumpulan_tugas_id')} "
                           f"section={section_code} path={image_url}")
            missing.append({
                "section_code": section_code,
                "image_url": image_url,
                "reason": "File tidak ditemukan di Storage",
            })

    return available, missing


def log_ai_run(
    submission_id: str,
    model_ai: str,
    started_at: str,
    completed_at: str,
    status: str,
    error_message: str = None
):
    """
    Catat eksekusi AI ke tabel audit_log.
    """
    try:
        from utils.audit_helper import create_audit_log, standardize_model_name
        from utils.supabase_client import supabase
        
        # Standardize model name
        model_ai = standardize_model_name(model_ai)
        
        if status == "success":
            total_score = None
            try:
                sub_res = supabase.table("pengumpulan_tugas").select("nilai_akhir").eq("id", submission_id).execute()
                if sub_res.data:
                    total_score = sub_res.data[0].get("nilai_akhir")
            except Exception as e:
                logger.error(f"[AI] Error fetching total score for logging: {e}", exc_info=True)
                
            create_audit_log(
                action="AI_PROCESS_COMPLETED",
                target="pengumpulan_tugas",
                detail={
                    "model": model_ai,
                    "total_score": total_score if total_score is not None else 0
                },
                role="dosen",
                user_name="Dosen"
            )
        else:
            create_audit_log(
                action="AI_PROCESS_FAILED",
                target="pengumpulan_tugas",
                detail={
                    "error": error_message or "Proses AI gagal tanpa detail pesan error."
                },
                role="dosen",
                user_name="Dosen"
            )
    except Exception as e:
        logger.error(f"[AI] Gagal menulis ke audit_log: {e}", exc_info=True)


def process_submission(submission_id: str, model_name: str = "MobileNetV2") -> dict:
    """
    Pipeline lengkap untuk satu submission.

    Termasuk pre-flight validasi file Storage sebelum inferensi dimulai.
    Jika seluruh file hilang, prediksi diblokir dan error jelas dikembalikan.
    """
    started_at = datetime.now().strftime("%Y-%m-%d %H:%M")
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

    # Guard against duplicate prediction/running processes
    ai_status = submission.get("ai_status")
    status_submit = submission.get("status_submit")
    
    if ai_status == "processing" or status_submit == "processing_ai":
        return {
            "success": False,
            "error": "Analisis AI sedang berjalan untuk tugas ini.",
            "already_running": True
        }
    if ai_status == "finalized" or status_submit == "finalized":
        return {
            "success": False,
            "error": "Tugas ini sudah difinalisasi dan tidak dapat dianalisis ulang.",
            "already_completed": True
        }

    normalized_model_name = _normalize_model_name(model_name)
    
    verbose = settings_service.get_setting("verbose_logging") == "true"
    if verbose:
        logger.info(f"[AI VERBOSE] [process_submission] Started processing submission={submission_id} using model={normalized_model_name}")

    # Log AI_PROCESS_STARTED
    try:
        from utils.audit_helper import create_audit_log
        create_audit_log(
            action="AI_PROCESS_STARTED",
            target="pengumpulan_tugas",
            detail={"model": normalized_model_name},
            role="dosen",
            user_name="Dosen"
        )
    except Exception as start_err:
        logger.error(f"[AI] Failed to log AI_PROCESS_STARTED: {start_err}", exc_info=True)

    # --------------------------------------------------
    # 2. Update status → processing & save model name
    # --------------------------------------------------
    try:
        from utils.supabase_client import supabase
        supabase.table("pengumpulan_tugas").update({
            "ai_status": "processing",
            "status_submit": "processing_ai",
            "model_ai": normalized_model_name
        }).eq("id", submission_id).execute()
    except Exception as e:
        warnings.append(f"Gagal mengupdate status awal ke processing: {e}")

    try:
        # Delete existing predictions for this submission to prevent duplication
        delete_predictions_by_submission(submission_id)
    except Exception as e:
        warnings.append(f"Gagal menghapus prediksi lama: {e}")

    try:
        # --------------------------------------------------
        # 3. Ambil semua lembar jawaban
        # --------------------------------------------------
        sheets = get_answer_sheets(submission_id)
        if not sheets:
            try:
                update_ai_status(submission_id, "failed")
            except Exception:
                pass
            completed_at = datetime.now().strftime("%Y-%m-%d %H:%M")
            log_ai_run(
                submission_id=submission_id,
                model_ai=normalized_model_name,
                started_at=started_at,
                completed_at=completed_at,
                status="failed",
                error_message="Tidak ada lembar jawaban untuk submission ini."
            )
            return {
                "success": False,
                "error": "Tidak ada lembar jawaban untuk submission ini.",
            }

        # --------------------------------------------------
        # 4. PRE-FLIGHT: Validasi file Storage
        # --------------------------------------------------
        available_sheets, missing_files = _validate_storage_files(sheets)

        # Jika ada minimal 1 file hilang → batalkan seluruh inferensi dan return error
        if len(missing_files) > 0:
            try:
                update_ai_status(submission_id, "failed")
            except Exception as e:
                logger.error(f"[AI] Gagal update_ai_status ke failed: {e}", exc_info=True)
            try:
                from utils.supabase_client import supabase
                supabase.table("pengumpulan_tugas").update({
                    "ai_status": "failed",
                    "status_submit": "failed",
                    "nilai_akhir": None
                }).eq("id", submission_id).execute()
            except Exception as e:
                logger.error(f"[AI] Gagal update direct ke failed: {e}", exc_info=True)
            
            missing_sections = [m["section_code"] for m in missing_files]
            logger.warning(f"[AI] Pre-flight check failed: {len(missing_files)} file tidak ditemukan "
                  f"dari total {len(sheets)} lembar jawaban untuk submission {submission_id}")
            logger.warning(f"[AI] Missing sections: {', '.join(missing_sections)}")
            
            error_msg = (
                f"Gagal memulai AI. Terdeteksi {len(missing_files)} file jawaban mahasiswa "
                f"yang tidak ditemukan di Storage untuk section: {', '.join(missing_sections)}. "
                f"Seluruh inferensi dibatalkan demi menjaga konsistensi jawaban."
            )
            completed_at = datetime.now().strftime("%Y-%m-%d %H:%M")
            log_ai_run(
                submission_id=submission_id,
                model_ai=normalized_model_name,
                started_at=started_at,
                completed_at=completed_at,
                status="failed",
                error_message=error_msg
            )
            return {
                "success": False,
                "error": error_msg,
                "ai_status": "failed",
                "missing_files": len(missing_files),
            }

        results = []
        errors = []

        # --------------------------------------------------
        # 5. Proses setiap sheet (hanya yang file-nya ada)
        # --------------------------------------------------
        for sheet in available_sheets:
            section_code = sheet.get("section_code", "unknown")
            try:
                result = process_single_sheet(sheet, model_name=normalized_model_name)
                results.append(result)
            except FileNotFoundError as e:
                # File hilang saat download (race condition)
                logger.error(f"[AI] File hilang saat download: submission={submission_id} "
                      f"section={section_code} error={str(e)}", exc_info=True)
                errors.append({
                    "section_code": section_code,
                    "error": f"File tidak ditemukan di Storage: {str(e)}",
                })
            except Exception as e:
                errors.append({
                    "section_code": section_code,
                    "error": str(e),
                })

        # --------------------------------------------------
        # 6. Hitung nilai_akhir
        # --------------------------------------------------
        nilai_akhir = sum(r["predicted_score"] for r in results)

        # --------------------------------------------------
        # 7. Tentukan status akhir
        # --------------------------------------------------
        if len(errors) == 0:
            ai_status = "completed"
        else:
            ai_status = "failed"
            # Hapus semua hasil prediksi parsial yang sempat tersimpan agar bersih
            try:
                delete_predictions_by_submission(submission_id)
            except Exception:
                pass

        # --------------------------------------------------
        # 8. Update submission
        # --------------------------------------------------
        try:
            update_submission_result(
                submission_id=submission_id,
                nilai_akhir=nilai_akhir if ai_status == "completed" else None,
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
                    "nilai_akhir": nilai_akhir if ai_status == "completed" else None,
                    "model_ai": normalized_model_name,
                    "ai_status": ai_status,
                    "status_submit": "submitted" if ai_status == "completed" else "failed",
                }).eq(
                    "id", submission_id
                ).execute()
            except Exception as fallback_err:
                warnings.append(f"Fallback update nilai_akhir/model_ai juga gagal: {fallback_err}")

        completed_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        if ai_status == "failed":
            error_msgs = [f"Section {err['section_code']}: {err['error']}" for err in errors]
            error_msg_str = "Proses AI gagal. Detail: " + "; ".join(error_msgs)
            log_ai_run(
                submission_id=submission_id,
                model_ai=normalized_model_name,
                started_at=started_at,
                completed_at=completed_at,
                status="failed",
                error_message=error_msg_str
            )
            return {
                "success": False,
                "error": error_msg_str,
                "submission_id": submission_id,
                "total_sheets": len(sheets),
                "processed": len(results),
                "failed": len(errors),
                "missing_files": 0,
                "nilai_akhir": None,
                "ai_status": "failed",
                "model_ai": normalized_model_name,
                "results": results,
                "errors": errors,
                "warnings": warnings,
            }

        log_ai_run(
            submission_id=submission_id,
            model_ai=normalized_model_name,
            started_at=started_at,
            completed_at=completed_at,
            status="success"
        )

        return {
            "success": True,
            "submission_id": submission_id,
            "total_sheets": len(sheets),
            "processed": len(results),
            "failed": 0,
            "missing_files": 0,
            "nilai_akhir": nilai_akhir,
            "ai_status": "completed",
            "model_ai": normalized_model_name,
            "results": results,
            "errors": [],
            "warnings": warnings,
        }
    except Exception as e:
        # Prevent the status from getting stuck in "processing" if something crashes completely
        try:
            delete_predictions_by_submission(submission_id)
        except Exception:
            pass
        try:
            update_ai_status(submission_id, "failed")
        except Exception:
            pass
        completed_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        log_ai_run(
            submission_id=submission_id,
            model_ai=normalized_model_name,
            started_at=started_at,
            completed_at=completed_at,
            status="failed",
            error_message=f"Terjadi kesalahan internal saat memproses AI: {str(e)}"
        )
        return {
            "success": False,
            "error": f"Terjadi kesalahan internal saat memproses AI: {str(e)}",
            "ai_status": "failed",
            "warnings": warnings,
        }

