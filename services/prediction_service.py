import numpy as np

from repositories.prediction_repository import upsert_prediction
from services.class_mapping import get_score
from services.image_service import download_image
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
        model_name = MODEL_AI

    lower = model_name.lower()
    if lower == "mobilenetv2":
        return "MobileNetV2"
    if lower == "densenet121":
        return "DenseNet121"
    if lower == "inceptionv3":
        return "InceptionV3"
    return model_name if model_name in MODEL_CONFIG else MODEL_AI


def process_single_sheet(sheet: dict, model_name: str = MODEL_AI) -> dict:
    """
    Proses satu lembar jawaban: download → preprocess → predict → save.

    Flow aktif AI berjalan melalui RQ worker:
    main.py → queue_service.enqueue_predictions() → tasks.process_batch_job()
    → process_single_sheet().

    Fungsi legacy `process_submission()` sengaja dihapus karena pipeline lama
    BackgroundTasks sudah tidak dipakai dan berisiko menulis pasangan
    status_submit/ai_status yang tidak valid terhadap constraint database.
    """
    section_code = sheet["section_code"]
    image_url = sheet["image_url"]
    lembar_jawaban_id = sheet["id"]
    pengumpulan_tugas_id = sheet["pengumpulan_tugas_id"]

    normalized_model_name = _normalize_model_name(model_name)

    verbose = settings_service.get_setting("verbose_logging") == "true"
    if verbose:
        logger.info(
            "[AI VERBOSE] [process_single_sheet] Starting section %s with model %s",
            section_code,
            normalized_model_name,
        )

    img = download_image(image_url)
    if img is None:
        raise ValueError(f"Gagal decode image untuk section {section_code}")

    if verbose:
        logger.info(
            "[AI VERBOSE] [process_single_sheet] Image downloaded successfully, size: %s",
            img.shape,
        )

    model_config = MODEL_CONFIG[normalized_model_name]
    input_size = model_config["input_size"]
    processed = preprocess_image(
        img,
        input_size,
        model_config.get("preprocessing", "BGR_TO_RGB_RESIZE_FLOAT32_DIVIDE_255"),
    )
    model = get_model(section_code, normalized_model_name)

    output = model.predict(processed, verbose=0)
    predicted_class = int(np.argmax(output[0]))
    confidence = float(np.max(output[0]))

    if verbose:
        logger.info(
            "[AI VERBOSE] [process_single_sheet] Section %s prediction raw output shape: %s, class: %s, confidence: %.4f",
            section_code,
            output.shape,
            predicted_class,
            confidence,
        )

    predicted_score = get_score(section_code, predicted_class)

    if verbose:
        logger.info(
            "[AI VERBOSE] [process_single_sheet] Section %s mapped score: %s",
            section_code,
            predicted_score,
        )

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
