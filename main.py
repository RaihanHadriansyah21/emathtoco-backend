import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from repositories.prediction_repository import get_predictions_by_submission
from repositories.submission_repository import get_submission_by_id, update_ai_status
from services.model_registry import get_cache_status
from services.prediction_service import process_submission
from utils.supabase_client import supabase

load_dotenv()

app = FastAPI(title="EMATHTOCO AI Backend Versi 1.0.0")
# ==================================================
# CORS CONFIGURATION
# ==================================================

# Default origins for local development
default_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

# Read ALLOWED_ORIGINS from environment variable (supports comma-separated values, optionally enclosed in brackets)
allowed_origins_env = os.getenv("ALLOWED_ORIGINS")
if allowed_origins_env:
    raw_origins = allowed_origins_env.strip()
    if raw_origins.startswith("[") and raw_origins.endswith("]"):
        raw_origins = raw_origins[1:-1]
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
else:
    origins = default_origins
print("=== ALLOWED ORIGINS ===")
print(origins)
print("=======================")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================================================
# PRODUCTION ENDPOINTS
# ==================================================


@app.post("/predict/{submission_id}")
def predict(submission_id: str, model: str = "MobileNetV2"):
    """
    Pipeline utama: jalankan AI untuk seluruh lembar jawaban
    milik submission_id.
    """
    if model not in ["MobileNetV2", "DenseNet201", "InceptionV3"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model. Allowed values: MobileNetV2, DenseNet201, InceptionV3"
        )
    
    submission = get_submission_by_id(submission_id)
    if not submission:
        raise HTTPException(
            status_code=404,
            detail=f"Submission dengan ID '{submission_id}' tidak ditemukan."
        )
    
    if submission.get("ai_status") == "finalized" or submission.get("status_submit") == "finalized":
        raise HTTPException(
            status_code=400,
            detail="Submission sudah finalized dan tidak dapat diprediksi ulang."
        )

    result = process_submission(submission_id, model_name=model)
    if not result.get("success") and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/prediction/{submission_id}")
def get_prediction(submission_id: str):
    """
    Mengambil hasil prediksi final untuk submission_id.
    """
    submission = get_submission_by_id(submission_id)
    if not submission:
        raise HTTPException(
            status_code=404,
            detail=f"Submission dengan ID '{submission_id}' tidak ditemukan.",
        )

    model_ai = submission.get("model_ai")
    predictions = get_predictions_by_submission(submission_id, model_ai)

    sections_dict = {}
    for pred in predictions:
        code = pred.get("section_code")
        # If there are duplicates, prioritize MobilenetV2 and non-debug scores (not 85)
        is_debug = pred.get("predicted_score") == 85
        if code in sections_dict:
            # If the existing one is debug and the new one is not, overwrite it
            if sections_dict[code]["predicted_score"] == 85 and not is_debug:
                sections_dict[code] = {
                    "section_code": code,
                    "predicted_class": pred.get("predicted_class"),
                    "predicted_score": pred.get("predicted_score"),
                    "confidence": round(float(pred.get("confidence", 0.0)), 2),
                }
        else:
            sections_dict[code] = {
                "section_code": code,
                "predicted_class": pred.get("predicted_class"),
                "predicted_score": pred.get("predicted_score"),
                "confidence": round(float(pred.get("confidence", 0.0)), 2),
            }

    # Sort the sections alphabetically (e.g. S-1A, S-1B...)
    sorted_sections = [sections_dict[k] for k in sorted(sections_dict.keys())]

    return {
        "submission_id": submission_id,
        "nilai_akhir": submission.get("nilai_akhir"),
        "ai_status": submission.get("ai_status"),
        "model_ai": model_ai,
        "sections": sorted_sections,
    }


@app.get("/submission/{submission_id}/results")
def get_submission_results(submission_id: str):
    """
    Mengambil hasil prediksi final untuk submission_id (format dosen).
    """
    submission = get_submission_by_id(submission_id)
    if not submission:
        raise HTTPException(
            status_code=404,
            detail=f"Submission dengan ID '{submission_id}' tidak ditemukan.",
        )

    model_ai = submission.get("model_ai")
    predictions = get_predictions_by_submission(submission_id, model_ai)

    sections_dict = {}
    for pred in predictions:
        code = pred.get("section_code")
        # If there are duplicates, prioritize MobilenetV2 and non-debug scores (not 85)
        is_debug = pred.get("predicted_score") == 85
        if code in sections_dict:
            # If the existing one is debug and the new one is not, overwrite it
            if sections_dict[code]["predicted_score"] == 85 and not is_debug:
                sections_dict[code] = {
                    "section_code": code,
                    "predicted_score": pred.get("predicted_score"),
                    "confidence": round(float(pred.get("confidence", 0.0)), 2),
                }
        else:
            sections_dict[code] = {
                "section_code": code,
                "predicted_score": pred.get("predicted_score"),
                "confidence": round(float(pred.get("confidence", 0.0)), 2),
            }

    # Sort the sections alphabetically (e.g. S-1A, S-1B...)
    sorted_sections = [sections_dict[k] for k in sorted(sections_dict.keys())]

    return {
        "submission_id": submission_id,
        "nilai_akhir": submission.get("nilai_akhir"),
        "ai_status": submission.get("ai_status"),
        "model_ai": model_ai,
        "sections": sorted_sections,
    }


@app.post("/submission/{submission_id}/reviewed")
def post_reviewed(submission_id: str):
    """
    Update status submission menjadi reviewed.
    """
    data = update_ai_status(submission_id, "reviewed")
    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"Submission dengan ID '{submission_id}' tidak ditemukan.",
        )
    return {"success": True, "data": data}


@app.post("/submission/{submission_id}/finalize")
def post_finalize(submission_id: str):
    """
    Update status submission menjadi finalized.
    """
    data = update_ai_status(submission_id, "finalized")
    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"Submission dengan ID '{submission_id}' tidak ditemukan.",
        )
    return {"success": True, "data": data}


@app.get("/health")
def health():
    """
    Endpoint untuk pengecekan kesehatan backend.
    """
    return {"status": "ok"}


@app.get("/model-info")
def model_info():
    """
    Mengambil informasi cache model registry.
    """
    status = get_cache_status()
    return {
        "loaded_models": status["total_loaded"],
        "total_models": status["total_available"],
        "cache": status,
    }


@app.get("/cache-status")
def cache_status():
    """Lihat model mana yang sudah ada di lazy-load cache."""
    return get_cache_status()


@app.get("/audit-models")
def audit_models():
    """
    Loop all models in MODEL_CONFIG and return details.
    """
    import os
    from services.model_registry import MODEL_CONFIG, get_model, _loaded_models

    audit_results = []
    for arch, config in MODEL_CONFIG.items():
        base_path = config["path"]
        input_size = config["input_size"]

        # Count h5 files in folder
        if not os.path.exists(base_path):
            audit_results.append({
                "architecture": arch,
                "model_count": 0,
                "input_shape": None,
                "output_shape": None,
                "load_status": "folder_not_found"
            })
            continue

        h5_files = [f for f in os.listdir(base_path) if f.endswith(".h5")]
        model_count = len(h5_files)

        # Load one model to check shape dynamically (e.g. S-1A or model_1a.h5)
        # S-1A is equivalent to model_1a.h5
        input_shape = None
        output_shape = None
        load_status = "lazy"

        # Check if any model for this architecture is loaded in cache
        cache_keys = [k for k in _loaded_models.keys() if k.startswith(arch)]
        if len(cache_keys) > 0:
            load_status = f"loaded_{len(cache_keys)}_models"

        # Try to load model_1a.h5 to get shape details
        try:
            test_model = get_model("S-1A", arch)
            input_shape = list(test_model.input_shape) if test_model.input_shape else [None, input_size[0], input_size[1], 3]
            output_shape = list(test_model.output_shape) if test_model.output_shape else None
        except Exception as e:
            print(f"Error loading test model for {arch}: {e}")

        audit_results.append({
            "architecture": arch,
            "model_count": model_count,
            "input_shape": input_shape,
            "output_shape": output_shape,
            "load_status": load_status
        })

    return audit_results


@app.get("/lecturer/class-summary")
def get_class_summary(lecturer_id: str):
    """
    Mengambil ringkasan statistik kelas dan mahasiswa yang diajar oleh dosen.
    """
    # 1. Dapatkan daftar mata_kuliah_id yang diajar oleh dosen
    assignments_res = (
        supabase.table("dosen_mata_kuliah")
        .select("mata_kuliah_id")
        .eq("dosen_id", lecturer_id)
        .execute()
    )
    course_ids = [a["mata_kuliah_id"] for a in assignments_res.data]
    
    if not course_ids:
        return {
            "total_classes": 0,
            "total_students": 0,
            "classes": []
        }
    
    # 2. Dapatkan daftar mahasiswa_id yang terdaftar di mata_kuliah tersebut
    enrollments_res = (
        supabase.table("mahasiswa_mata_kuliah")
        .select("mahasiswa_id")
        .in_("mata_kuliah_id", course_ids)
        .execute()
    )
    student_ids = list(set([e["mahasiswa_id"] for e in enrollments_res.data]))
    
    if not student_ids:
        return {
            "total_classes": 0,
            "total_students": 0,
            "classes": []
        }
        
    # 3. Ambil data profil mahasiswa untuk mendapatkan kelas mereka
    students_res = (
        supabase.table("profil_pengguna")
        .select("id, kelas")
        .in_("id", student_ids)
        .execute()
    )
    
    # 4. Hitung jumlah mahasiswa per kelas
    classes_map = {}
    for student in students_res.data:
        # Normalisasi nama kelas, ganti empty/None dengan "-"
        kelas = (student.get("kelas") or "").strip()
        if not kelas:
            kelas = "-"
        classes_map[kelas] = classes_map.get(kelas, 0) + 1
        
    # 5. Format hasil
    classes_list = [{"kelas": k, "students": v} for k, v in sorted(classes_map.items())]
    
    return {
        "total_classes": len(classes_list),
        "total_students": len(students_res.data),
        "classes": classes_list
    }


@app.get("/ai-models")
def get_ai_models():
    """
    Registry model AI yang digunakan oleh sistem penilaian otomatis.
    """
    import os
    from services.model_registry import MODEL_CONFIG, _loaded_models
    
    models_list = []
    for arch, config in MODEL_CONFIG.items():
        base_path = config["path"]
        input_size = config["input_size"]
        
        # Count models dynamically
        total_models = 0
        if os.path.exists(base_path):
            total_models = len([f for f in os.listdir(base_path) if f.endswith(".h5")])
        
        # Check if loaded (at least one model of this architecture is in _loaded_models cache)
        is_loaded = any(k.startswith(arch) for k in _loaded_models.keys())
        
        # input_shape is [height, width, channels]
        input_shape = [input_size[0], input_size[1], 3]
        
        models_list.append({
            "name": arch,
            "loaded": is_loaded,
            "input_shape": input_shape,
            "total_models": total_models if total_models > 0 else 24
        })
        
    return {
        "success": True,
        "models": models_list
    }


@app.get("/lecturer/course/{course_id}/stats")
def get_course_stats(course_id: str):
    """
    Mengambil data statistik mahasiswa terdaftar untuk course_id.
    """
    try:
        # Hitung jumlah mahasiswa di mahasiswa_mata_kuliah
        res = (
            supabase.table("mahasiswa_mata_kuliah")
            .select("mahasiswa_id", count="exact")
            .eq("mata_kuliah_id", course_id)
            .execute()
        )
        total_students = res.count if res.count is not None else len(res.data)
        
        return {
            "success": True,
            "course_id": course_id,
            "total_students": total_students
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


