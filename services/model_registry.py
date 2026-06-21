import os
from services.model_loader import load_mobilenet_model

MODEL_CONFIG = {
    "MobileNetV2": {
        "path": "Models/MobilenetV2",
        "input_size": (128, 128)
    },
    "DenseNet121": {
        "path": "Models/DenseNet121",
        "input_size": (128, 128)
    },
    "InceptionV3": {
        "path": "Models/InceptionV3",
        "input_size": (299, 299)
    }
}

# Keep backward compatibility with old code that imports MODEL_MAP or refers to it
MODEL_MAP = {
    "S-1A": "Models/MobilenetV2/model_1a.h5",
    "S-1B": "Models/MobilenetV2/model_1b.h5",
    "S-1C": "Models/MobilenetV2/model_1c.h5",
    "S-1D": "Models/MobilenetV2/model_1d.h5",
    "S-1E": "Models/MobilenetV2/model_1e.h5",
    "S-1F": "Models/MobilenetV2/model_1f.h5",
    "S-2A": "Models/MobilenetV2/model_2a.h5",
    "S-2B": "Models/MobilenetV2/model_2b.h5",
    "S-2C": "Models/MobilenetV2/model_2c.h5",
    "S-2D": "Models/MobilenetV2/model_2d.h5",
    "S-2E": "Models/MobilenetV2/model_2e.h5",
    "S-2F": "Models/MobilenetV2/model_2f.h5",
    "S-3A": "Models/MobilenetV2/model_3a.h5",
    "S-3B": "Models/MobilenetV2/model_3b.h5",
    "S-3C": "Models/MobilenetV2/model_3c.h5",
    "S-3D": "Models/MobilenetV2/model_3d.h5",
    "S-3E": "Models/MobilenetV2/model_3e.h5",
    "S-3F": "Models/MobilenetV2/model_3f.h5",
    "S-4A": "Models/MobilenetV2/model_4a.h5",
    "S-4B": "Models/MobilenetV2/model_4b.h5",
    "S-4C": "Models/MobilenetV2/model_4c.h5",
    "S-4D": "Models/MobilenetV2/model_4d.h5",
    "S-4E": "Models/MobilenetV2/model_4e.h5",
    "S-4F": "Models/MobilenetV2/model_4f.h5",
}

# ==================================================
# LAZY LOADING CACHE with LRU Eviction Policy (Prevents OOM)
# Key format: f"{model_name}_{section_code}"
# ==================================================
from collections import OrderedDict
import tensorflow as tf
from utils.logging_helper import logger

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
    base_path = config["path"]

    parts = section_code.split("-")
    if len(parts) == 2:
        file_name = f"model_{parts[1].lower()}.h5"
    else:
        file_name = f"model_{section_code.lower()}.h5"

    model_path = os.path.join(base_path, file_name)
    cache_key = f"{normalized_model_name}_{section_code}"

    if cache_key in _loaded_models:
        # Move to end to mark as Most Recently Used (MRU)
        _loaded_models.move_to_end(cache_key)
    else:
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
            
        # Evict oldest model if cache size exceeds limit
        if len(_loaded_models) >= MAX_CACHED_MODELS:
            oldest_key, oldest_model = _loaded_models.popitem(last=False)
            logger.info(f"[Model Cache Eviction] Evicting model {oldest_key} to release memory.")
            del oldest_model
            tf.keras.backend.clear_session()
            
        _loaded_models[cache_key] = load_mobilenet_model(model_path)

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
