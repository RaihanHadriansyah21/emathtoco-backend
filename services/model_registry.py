import gc
import json
from collections import OrderedDict
from pathlib import Path

from config import get_settings
from services.model_manifest import ManifestValidationError, normalize_model_manifest
from services.model_loader import load_mobilenet_model
from utils.logging_helper import logger

MODEL_ROOT = Path(get_settings().model_root).expanduser().resolve()


def _resolve_model_dir(*candidates: str) -> Path:
    """
    Resolve folder arsitektur model dengan kompatibilitas casing.

    Model lama memakai `MobilenetV2`, sedangkan model baru memakai
    `MobileNetV2`. VPS/Linux case-sensitive, jadi path tidak boleh diasumsikan.
    """
    for candidate in candidates:
        path = MODEL_ROOT / candidate
        if path.is_dir():
            return path
    return MODEL_ROOT / candidates[0]


def _manifest_runtime_metadata() -> dict[str, dict]:
    manifest_path = MODEL_ROOT / "manifest.json"
    if not manifest_path.is_file():
        return {}
    try:
        manifest = normalize_model_manifest(
            json.loads(manifest_path.read_text(encoding="utf-8"))
        )
    except (OSError, json.JSONDecodeError, ManifestValidationError):
        return {}

    metadata: dict[str, dict] = {}
    for artifact in manifest.get("artifacts", []):
        architecture = artifact.get("architecture")
        input_shape = artifact.get("input_shape")
        if not architecture or architecture in metadata:
            continue
        if (
            isinstance(input_shape, list)
            and len(input_shape) >= 2
            and isinstance(input_shape[0], int)
            and isinstance(input_shape[1], int)
        ):
            input_size = (input_shape[0], input_shape[1])
        else:
            input_size = None
        metadata[architecture] = {
            "input_size": input_size,
            "preprocessing": artifact.get("preprocessing"),
        }
    return metadata


_MANIFEST_METADATA = _manifest_runtime_metadata()


def _input_size_for(architecture: str, fallback: tuple[int, int]) -> tuple[int, int]:
    return _MANIFEST_METADATA.get(architecture, {}).get("input_size") or fallback


def _preprocessing_for(architecture: str) -> str:
    return (
        _MANIFEST_METADATA.get(architecture, {}).get("preprocessing")
        or "BGR_TO_RGB_RESIZE_FLOAT32_DIVIDE_255"
    )

MODEL_CONFIG = {
    "MobileNetV2": {
        "path": _resolve_model_dir("MobileNetV2", "MobilenetV2"),
        "input_size": _input_size_for("MobileNetV2", (128, 128)),
        "preprocessing": _preprocessing_for("MobileNetV2"),
    },
    "DenseNet121": {
        "path": _resolve_model_dir("DenseNet121"),
        "input_size": _input_size_for("DenseNet121", (128, 128)),
        "preprocessing": _preprocessing_for("DenseNet121"),
    },
    "InceptionV3": {
        "path": _resolve_model_dir("InceptionV3"),
        "input_size": _input_size_for("InceptionV3", (299, 299)),
        "preprocessing": _preprocessing_for("InceptionV3"),
    }
}

# Keep backward compatibility with old code that imports MODEL_MAP or refers to it
MODEL_MAP = {
    section: str(MODEL_CONFIG["MobileNetV2"]["path"] / f"model_{section[2:].lower()}.h5")
    for section in (
        f"S-{question}{part}"
        for question in range(1, 5)
        for part in ("A", "B", "C", "D", "E", "F")
    )
}

# ==================================================
# LAZY LOADING CACHE with LRU Eviction Policy (Prevents OOM)
# Key format: f"{model_name}_{section_code}"
# ==================================================
MAX_CACHED_MODELS = 6
_loaded_models = OrderedDict()


def get_model(section_code: str, model_name: str = "MobileNetV2"):
    """
    Ambil model untuk section dan arsitektur tertentu.
    Menggunakan LRU eviction policy agar memory tetap stabil.
    """
    normalized_model_name = model_name
    if not model_name:
        normalized_model_name = "MobileNetV2"
    elif model_name.lower() == "mobilenetv2":
        normalized_model_name = "MobileNetV2"
    elif model_name.lower() == "densenet121":
        normalized_model_name = "DenseNet121"
    elif model_name.lower() == "inceptionv3":
        normalized_model_name = "InceptionV3"

    if normalized_model_name not in MODEL_CONFIG:
        normalized_model_name = "MobileNetV2"

    config = MODEL_CONFIG[normalized_model_name]
    base_path = Path(config["path"])

    parts = section_code.split("-")
    if len(parts) == 2:
        file_name = f"model_{parts[1].lower()}.h5"
    else:
        file_name = f"model_{section_code.lower()}.h5"

    model_path = (base_path / file_name).resolve()
    cache_key = f"{normalized_model_name}_{section_code}"

    if cache_key in _loaded_models:
        # Move to end to mark as Most Recently Used (MRU)
        _loaded_models.move_to_end(cache_key)
    else:
        if not model_path.is_file():
            raise FileNotFoundError(f"Model file not found: {model_path}")
            
        # Evict oldest model if cache size exceeds limit
        if len(_loaded_models) >= MAX_CACHED_MODELS:
            oldest_key, oldest_model = _loaded_models.popitem(last=False)
            logger.info(f"[Model Cache Eviction] Evicting model {oldest_key} to release memory.")
            del oldest_model
            gc.collect()
            
        _loaded_models[cache_key] = load_mobilenet_model(str(model_path))

    return _loaded_models[cache_key]


def get_cache_status() -> dict:
    """
    Return status cache untuk monitoring/debug.
    """
    loaded = list(_loaded_models.keys())
    
    all_sections = [
        f"S-{num}{sec.upper()}"
        for num in [1, 2, 3, 4]
        for sec in ['a', 'b', 'c', 'd', 'e', 'f']
    ]
    all_keys = [
        f"{m}_{s}"
        for m in MODEL_CONFIG.keys()
        for s in all_sections
    ]
    not_loaded = [k for k in all_keys if k not in loaded]
    
    return {
        "loaded": loaded,
        "not_loaded": not_loaded,
        "total_loaded": len(loaded),
        "total_available": len(all_keys),
    }
