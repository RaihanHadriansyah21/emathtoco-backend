import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from repositories.prediction_repository import get_predictions_by_submission
from repositories.submission_repository import get_submission_by_id, update_ai_status
from services.model_registry import get_cache_status
from services.prediction_service import process_submission
from services.settings_service import settings_service
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

# Ensure default local origins are always whitelisted
for default_origin in default_origins:
    if default_origin not in origins:
        origins.append(default_origin)

# Apply CORS middleware with whitelisted origins, dynamic regex for vercel/local subdomains, and enable credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https?://([^/]+\.)?(vercel\.app|localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================================================
# PRODUCTION ENDPOINTS
# ==================================================


@app.post("/predict/{submission_id}")
def predict(submission_id: str, model: str = None):
    """
    Pipeline utama: jalankan AI untuk seluruh lembar jawaban
    milik submission_id.
    """
    # Priority:
    # 1. Explicit model from parameter
    # 2. Global active model from database settings
    # 3. Fallback MobileNetV2
    if not model or model.lower() in ["", "none", "null"]:
        model = settings_service.get_setting("active_model")
    if not model:
        model = "MobileNetV2"

    if model not in ["MobileNetV2", "DenseNet121", "InceptionV3"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model. Allowed values: MobileNetV2, DenseNet121, InceptionV3"
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
    
    if submission.get("ai_status") == "processing":
        raise HTTPException(
            status_code=409,
            detail="Analisis AI sedang berjalan untuk tugas ini. Silakan tunggu hingga selesai."
        )

    result = process_submission(submission_id, model_name=model)
    if not result.get("success") and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/settings")
def get_settings():
    """Retrieve all system settings from the database (SST)."""
    return settings_service.get_all_settings()


@app.post("/settings")
def update_settings(payload: dict):
    """
    Update specified system settings in the database.
    Updates in-memory cache and logs audit logs:
    - SYSTEM_SETTING_CHANGED for general configs
    - ACTIVE_MODEL_CHANGED for active_model changes
    """
    from utils.audit_helper import create_audit_log
    
    changed_by = payload.get("changed_by", "Administrator")
    role = payload.get("role", "admin")
    user_id = payload.get("user_id", None)
    
    updates = payload.get("settings", {})
    if not updates:
        updates = {k: v for k, v in payload.items() if k not in ["changed_by", "role", "user_id"]}

    success = True
    for key, value in updates.items():
        old_value = settings_service.get_setting(key)
        
        if old_value == value:
            continue
            
        ok = settings_service.set_setting(key, str(value))
        if not ok:
            success = False
            continue
            
        if key == "active_model":
            create_audit_log(
                action="ACTIVE_MODEL_CHANGED",
                target="ai_models",
                detail={
                    "old_model": old_value,
                    "new_model": value,
                    "changed_by": changed_by
                },
                user_id=user_id,
                user_name=changed_by,
                role=role
            )
        else:
            create_audit_log(
                action="SYSTEM_SETTING_CHANGED",
                target="system",
                detail={
                    "setting_key": key,
                    "old_value": old_value,
                    "new_value": value,
                    "changed_by": changed_by
                },
                user_id=user_id,
                user_name=changed_by,
                role=role
            )
            
    if not success:
        raise HTTPException(status_code=500, detail="Gagal memperbarui beberapa pengaturan.")
        
    return {"success": True, "settings": settings_service.get_all_settings()}


def run_prediction_background(submission_id: str, model_name: str):
    try:
        process_submission(submission_id, model_name=model_name)
    except Exception as e:
        print(f"[AI Background] Error running prediction for {submission_id}: {e}")


@app.post("/submission/{submission_id}/submit")
def submit_submission(submission_id: str, background_tasks: BackgroundTasks):
    """
    Endpoint dipanggil saat mahasiswa klik kumpulkan tugas.
    Membaca setting auto_run_ai dari database.
    Jika ON: Jalankan pipeline AI di background.
    Jika OFF: Kembalikan respon sukses tanpa memproses AI.
    """
    submission = get_submission_by_id(submission_id)
    if not submission:
        raise HTTPException(
            status_code=404,
            detail=f"Submission dengan ID '{submission_id}' tidak ditemukan."
        )
        
    auto_run = settings_service.get_setting("auto_run_ai") == "true"
    
    if not auto_run:
        return {
            "success": True,
            "message": "Submission submitted successfully. Auto-run AI is disabled.",
            "auto_run": False
        }
        
    ai_status = submission.get("ai_status")
    status_submit = submission.get("status_submit")
    
    if ai_status == "processing" or status_submit == "processing_ai":
        return {
            "success": True,
            "message": "AI is already processing for this submission.",
            "auto_run": True,
            "already_running": True
        }
        
    if ai_status in ["completed", "reviewed", "finalized"] or status_submit in ["reviewed", "finalized"]:
        return {
            "success": True,
            "message": "AI prediction has already completed for this submission.",
            "auto_run": True,
            "already_completed": True
        }
        
    model_name = settings_service.get_setting("active_model")
    if not model_name:
        model_name = "MobileNetV2"
        
    background_tasks.add_task(run_prediction_background, submission_id, model_name)
    
    return {
        "success": True,
        "message": f"Submission submitted. AI triggered in background using model {model_name}.",
        "auto_run": True
    }


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
    return {
        "status": "ok",
        "service": "EMATHTOCO AI Backend"
    }


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


@app.post("/admin/predictions/count")
def admin_count_predictions(payload: dict):
    lembar_jawaban_ids = payload.get("lembar_jawaban_ids", [])
    if not lembar_jawaban_ids:
        return {"count": 0}
    try:
        res = supabase.table("hasil_prediksi").select("id", count="exact").in_("lembar_jawaban_id", lembar_jawaban_ids).execute()
        return {"count": res.count if res.count is not None else len(res.data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/predictions/delete")
def admin_delete_predictions(payload: dict):
    lembar_jawaban_ids = payload.get("lembar_jawaban_ids", [])
    if not lembar_jawaban_ids:
        return {"deleted": 0}
    try:
        res = supabase.table("hasil_prediksi").delete().in_("lembar_jawaban_id", lembar_jawaban_ids).execute()
        return {"deleted": len(res.data) if res.data else 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/audit/schema-check")
def audit_schema_check():
    """
    Checks the schema version of the audit_log table.
    Returns whether it is using the legacy schema or the new enterprise schema,
    along with the list of columns found.
    """
    import requests
    from utils.supabase_client import SUPABASE_URL, SUPABASE_KEY
    import utils.audit_helper as audit_helper

    columns_found = []
    
    # Method 1: Check OpenAPI Spec from Postgrest
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        r = requests.get(f"{SUPABASE_URL}/rest/v1/", headers=headers, timeout=5)
        if r.status_code == 200:
            spec = r.json()
            definitions = spec.get("definitions", {})
            audit_log_def = definitions.get("audit_log", {})
            properties = audit_log_def.get("properties", {})
            columns_found = list(properties.keys())
    except Exception as e:
        print(f"[AUDIT] OpenAPI check failed: {e}")

    # Method 2 (Fallback/Verification): Select columns limit 0
    if not columns_found:
        test_columns = [
            "id", "actor_id", "actor_role", "action_type", "target_type", "target_id", 
            "description", "created_at", "user_id", "user_name", "role", "action", "target", "detail"
        ]
        for col in test_columns:
            try:
                supabase.table("audit_log").select(col).limit(0).execute()
                columns_found.append(col)
            except Exception:
                pass

    # Determine schema version
    new_columns = {"user_id", "user_name", "role", "action", "target", "detail"}
    has_all_new = new_columns.issubset(set(columns_found))
    schema_version = "enterprise" if has_all_new else "legacy"

    # Synchronize the global cache in audit_helper.py
    audit_helper._HAS_ENTERPRISE_SCHEMA = has_all_new

    return {
        "schema_version": schema_version,
        "columns_found": columns_found
    }


@app.post("/audit/log")
def post_audit_log(payload: dict):
    """
    Endpoint untuk menerima penulisan audit log dari frontend.
    Memvalidasi dan menormalisasi payload sebelum diteruskan ke database.
    """
    if not payload:
        raise HTTPException(status_code=400, detail="Payload kosong.")
    
    # Required fields validation
    action = payload.get("action")
    target = payload.get("target")
    
    if not action or not target:
        raise HTTPException(status_code=400, detail="Field 'action' dan 'target' wajib diisi.")
        
    user_id = payload.get("user_id")
    user_name = payload.get("user_name")
    role = payload.get("role")
    detail = payload.get("detail")

    # Standardize/Normalize model names
    from utils.audit_helper import standardize_model_name, create_audit_log
    
    action = standardize_model_name(action)
    target = standardize_model_name(target)
    
    if isinstance(detail, str):
        detail = standardize_model_name(detail)
    elif isinstance(detail, dict):
        # normalize values inside detail dict if string
        for k, v in detail.items():
            if isinstance(v, str):
                detail[k] = standardize_model_name(v)

    success = create_audit_log(
        action=action,
        target=target,
        detail=detail,
        user_id=user_id,
        user_name=user_name,
        role=role
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Gagal menulis rekam audit ke database.")
        
    return {"success": True}


@app.get("/audit/test")
def audit_test():
    """
    Endpoint test untuk memverifikasi penulisan log terpusat.
    """
    from utils.audit_helper import create_audit_log
    success = create_audit_log(
        action="AUDIT_TEST",
        target="system",
        detail={"test": "pusat logging backend works!"},
        user_id=None,
        user_name="System Test",
        role="system"
    )
    if not success:
        raise HTTPException(status_code=500, detail="Gagal menulis log uji.")
    return {"success": True}



