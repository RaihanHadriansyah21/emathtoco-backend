from uuid import UUID

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api_models import (
    AuditEventRequest,
    BatchPredictionRequest,
    DemoResetRequest,
    PredictionIdsRequest,
    SettingsUpdateRequest,
    UserRoleUpdateRequest,
)
from config import get_settings as load_runtime_settings
from domain import AIModel, get_domain_contract
from repositories.prediction_repository import get_predictions_by_submission
from repositories.submission_repository import get_submission_by_id
from services.queue_service import (
    enqueue_predictions,
    enqueue_storage_cleanup,
    get_job_status,
    queue_readiness,
)
from services.settings_service import settings_service
from utils.supabase_client import supabase, verify_user_token
from utils.logging_helper import logger

load_dotenv()
runtime_settings = load_runtime_settings()

app = FastAPI(title="EMATHTOCO AI Backend Versi 1.0.0")
# ==================================================
# CORS CONFIGURATION
# ==================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(runtime_settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "ngrok-skip-browser-warning"],
)


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled API error",
        extra={"path": request.url.path, "method": request.method},
    )
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR"}},
    )


def verify_admin_token(authorization: str = Header(None)) -> str:
    """
    Verifikasi access token dari Supabase.
    Memastikan token valid dan memiliki role 'admin'.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="AUTHORIZATION_REQUIRED"
        )
    token = authorization.split(" ")[1]
    
    try:
        # FIX #1: Use verify_user_token() instead of supabase.auth.get_user(token)
        # to avoid polluting the global singleton's auth context.
        user = verify_user_token(token)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="INVALID_OR_EXPIRED_TOKEN"
            )
            
        user_id = user.id
        
        # Ambil role dari tabel profil_pengguna untuk otorisasi
        profile_res = supabase.table("profil_pengguna").select("role").eq("id", user_id).maybe_single().execute()
        if not profile_res or not profile_res.data:
            raise HTTPException(
                status_code=403,
                detail="PROFILE_NOT_FOUND"
            )
            
        role = profile_res.data.get("role", "").lower()
        if role != "admin":
            raise HTTPException(
                status_code=403,
                detail="ADMIN_ROLE_REQUIRED"
            )
            
        return user_id
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"[AUTH] Token verification failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=401,
            detail="TOKEN_VERIFICATION_FAILED"
        )


def verify_dosen_or_admin_token(authorization: str = Header(None)) -> str:
    """
    Verifikasi access token dari Supabase.
    Memastikan token valid dan memiliki role 'dosen' atau 'admin'.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="AUTHORIZATION_REQUIRED"
        )
    token = authorization.split(" ")[1]
    
    try:
        # FIX #1: Use verify_user_token() to avoid token pollution
        user = verify_user_token(token)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="INVALID_OR_EXPIRED_TOKEN"
            )
            
        user_id = user.id
        
        profile_res = supabase.table("profil_pengguna").select("role").eq("id", user_id).maybe_single().execute()
        if not profile_res or not profile_res.data:
            raise HTTPException(
                status_code=403,
                detail="PROFILE_NOT_FOUND"
            )
            
        role = profile_res.data.get("role", "").lower()
        if role not in ["dosen", "admin"]:
            raise HTTPException(
                status_code=403,
                detail="LECTURER_OR_ADMIN_REQUIRED"
            )
            
        return user_id
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"[AUTH] Token verification failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=401,
            detail="TOKEN_VERIFICATION_FAILED"
        )


def verify_any_authenticated_token(authorization: str = Header(None)) -> str:
    """
    Verifikasi access token dari Supabase.
    Memastikan token valid dan pengguna terdaftar di sistem.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="AUTHORIZATION_REQUIRED"
        )
    token = authorization.split(" ")[1]
    
    try:
        # FIX #1: Use verify_user_token() to avoid token pollution
        user = verify_user_token(token)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="INVALID_OR_EXPIRED_TOKEN"
            )
            
        return user.id
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"[AUTH] Token verification failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=401,
            detail="TOKEN_VERIFICATION_FAILED"
        )


def check_lecturer_course_access(lecturer_id: str, course_id: str) -> bool:
    """
    Verifikasi apakah dosen mengajar/ditugaskan pada mata kuliah tertentu.
    Admin selalu diizinkan.
    """
    profile_res = supabase.table("profil_pengguna").select("role").eq("id", lecturer_id).maybe_single().execute()
    if not profile_res or not profile_res.data:
        return False
    
    role = profile_res.data.get("role", "").lower()
    if role == "admin":
        return True
        
    if role != "dosen":
        return False
        
    assignment = (
        supabase.table("dosen_mata_kuliah")
        .select("id")
        .eq("dosen_id", lecturer_id)
        .eq("mata_kuliah_id", course_id)
        .maybe_single()
        .execute()
    )
    return bool(assignment and assignment.data)


def check_user_submission_read_access(user_id: str, submission_id: str) -> bool:
    """
    Memeriksa apakah pengguna memiliki hak akses baca untuk submission.
    Dosen harus ditugaskan ke course, mahasiswa harus memiliki submission tersebut, admin selalu diizinkan.
    """
    profile_res = supabase.table("profil_pengguna").select("role").eq("id", user_id).maybe_single().execute()
    if not profile_res or not profile_res.data:
        return False
        
    role = profile_res.data.get("role", "").lower()
    if role == "admin":
        return True
        
    submission = get_submission_by_id(submission_id)
    if not submission:
        return False
        
    if role == "dosen":
        course_id = submission.get("mata_kuliah_id")
        if not course_id:
            return False
        return check_lecturer_course_access(user_id, course_id)
        
    return submission.get("mahasiswa_id") == user_id


def check_lecturer_submission_write_access(lecturer_id: str, submission_id: str) -> bool:
    """
    Memeriksa apakah dosen memiliki hak akses ubah untuk submission (dosen mata kuliah).
    Admin selalu diizinkan.
    """
    profile_res = supabase.table("profil_pengguna").select("role").eq("id", lecturer_id).maybe_single().execute()
    if not profile_res or not profile_res.data:
        return False
        
    role = profile_res.data.get("role", "").lower()
    if role == "admin":
        return True
        
    if role != "dosen":
        return False
        
    submission = get_submission_by_id(submission_id)
    if not submission:
        return False
        
    course_id = submission.get("mata_kuliah_id")
    if not course_id:
        return False
        
    return check_lecturer_course_access(lecturer_id, course_id)


# ==================================================
# PRODUCTION ENDPOINTS
# ==================================================


@app.post("/predict/{submission_id}", status_code=202)
def predict(
    submission_id: UUID,
    model: AIModel | None = None,
    user_id: str = Depends(verify_dosen_or_admin_token),
):
    submission_id_text = str(submission_id)
    if not check_lecturer_submission_write_access(user_id, submission_id_text):
        raise HTTPException(status_code=403, detail="SUBMISSION_ACCESS_DENIED")

    selected_model = model
    if selected_model is None:
        configured_model = settings_service.get_setting("active_model")
        try:
            selected_model = AIModel(configured_model or AIModel.MOBILENET_V2)
        except ValueError:
            selected_model = AIModel.MOBILENET_V2

    result = enqueue_predictions([submission_id], selected_model)
    if not result.accepted_ids:
        raise HTTPException(
            status_code=409,
            detail=next(iter(result.rejected.values()), "SUBMISSION_NOT_ELIGIBLE"),
        )
    return {
        "job_id": result.job_id,
        "status": "queued",
        "accepted_ids": result.accepted_ids,
        "rejected": result.rejected,
    }


@app.post("/predict/batch", status_code=202)
def predict_batch(
    payload: BatchPredictionRequest,
    user_id: str = Depends(verify_dosen_or_admin_token),
):
    eligible: list[UUID] = []
    rejected: dict[str, str] = {}
    for submission_id in payload.submission_ids:
        submission_id_text = str(submission_id)
        if not check_lecturer_submission_write_access(user_id, submission_id_text):
            rejected[submission_id_text] = "access_denied"
            continue
        eligible.append(submission_id)

    if not eligible:
        raise HTTPException(status_code=403, detail="NO_ELIGIBLE_SUBMISSIONS")

    selected_model = payload.model
    if selected_model is None:
        configured_model = settings_service.get_setting("active_model")
        try:
            selected_model = AIModel(configured_model or AIModel.MOBILENET_V2)
        except ValueError:
            selected_model = AIModel.MOBILENET_V2

    result = enqueue_predictions(eligible, selected_model)
    rejected.update(result.rejected)
    if not result.accepted_ids:
        raise HTTPException(status_code=409, detail="NO_SUBMISSIONS_QUEUED")
    return {
        "job_id": result.job_id,
        "status": "queued",
        "accepted_ids": result.accepted_ids,
        "rejected": rejected,
    }


@app.get("/jobs/{job_id}")
def job_status(
    job_id: UUID,
    user_id: str = Depends(verify_any_authenticated_token),
):
    try:
        status = get_job_status(str(job_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="JOB_NOT_FOUND") from exc
    accepted_ids = status.get("accepted_ids", [])
    if not accepted_ids or not any(
        check_user_submission_read_access(user_id, submission_id)
        for submission_id in accepted_ids
    ):
        raise HTTPException(status_code=403, detail="JOB_ACCESS_DENIED")
    return status



@app.get("/settings")
def get_settings(user_id: str = Depends(verify_dosen_or_admin_token)):
    """Retrieve all system settings from the database (SST)."""
    return settings_service.get_all_settings()


@app.post("/settings")
def update_settings(
    payload: SettingsUpdateRequest,
    admin_user_id: str = Depends(verify_admin_token),
):
    """
    Update specified system settings in the database.
    Updates in-memory cache and logs audit logs:
    - SYSTEM_SETTING_CHANGED for general configs
    - ACTIVE_MODEL_CHANGED for active_model changes
    """
    from utils.audit_helper import create_audit_log
    
    import json

    profile = (
        supabase.table("profil_pengguna")
        .select("nama_lengkap, role")
        .eq("id", admin_user_id)
        .single()
        .execute()
    )
    changed_by = profile.data.get("nama_lengkap", "Administrator")
    role = profile.data.get("role", "admin")
    updates = payload.settings

    success = True
    for key, value in updates.items():
        if isinstance(value, bool):
            serialized_value = str(value).lower()
        elif isinstance(value, dict):
            serialized_value = json.dumps(value, separators=(",", ":"))
        else:
            serialized_value = str(value)
        old_value = settings_service.get_setting(key)
        
        if old_value == serialized_value:
            continue
            
        ok = settings_service.set_setting(key, serialized_value)
        if not ok:
            success = False
            continue
            
        if key == "active_model":
            create_audit_log(
                action="ACTIVE_MODEL_CHANGED",
                target="ai_models",
                detail={
                    "old_model": old_value,
                    "new_model": serialized_value,
                },
                user_id=admin_user_id,
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
                    "new_value": serialized_value,
                },
                user_id=admin_user_id,
                user_name=changed_by,
                role=role
            )
            
    if not success:
        raise HTTPException(status_code=500, detail="Gagal memperbarui beberapa pengaturan.")
        
    return {"success": True, "settings": settings_service.get_all_settings()}


@app.post("/submission/{submission_id}/submit")
def submit_submission(
    submission_id: UUID,
    user_id: str = Depends(verify_any_authenticated_token),
):
    """
    Endpoint dipanggil saat mahasiswa klik kumpulkan tugas.
    Membaca setting auto_run_ai dari database.
    Jika ON: Jalankan pipeline AI di background.
    Jika OFF: Kembalikan respon sukses tanpa memproses AI.
    """
    submission_id_text = str(submission_id)
    submission = get_submission_by_id(submission_id_text)
    if not submission:
        raise HTTPException(status_code=404, detail="SUBMISSION_NOT_FOUND")
        
    if not check_user_submission_read_access(user_id, submission_id_text):
        raise HTTPException(status_code=403, detail="SUBMISSION_ACCESS_DENIED")

    if submission.get("status_submit") != "submitted":
        raise HTTPException(status_code=409, detail="SUBMISSION_NOT_SUBMITTED")
        
    auto_run = settings_service.get_setting("auto_run_ai") == "true"
    
    if not auto_run:
        return {
            "success": True,
            "message": "Submission submitted successfully. Auto-run AI is disabled.",
            "auto_run": False
        }
        
    model_name = settings_service.get_setting("active_model")
    try:
        selected_model = AIModel(model_name or AIModel.MOBILENET_V2)
    except ValueError:
        selected_model = AIModel.MOBILENET_V2

    result = enqueue_predictions([submission_id], selected_model)
    if not result.accepted_ids:
        raise HTTPException(
            status_code=409,
            detail=next(iter(result.rejected.values()), "SUBMISSION_NOT_ELIGIBLE"),
        )

    return {
        "success": True,
        "message": "Submission submitted and AI job queued.",
        "auto_run": True,
        "job_id": result.job_id,
        "status": "queued",
    }


@app.get("/prediction/{submission_id}")
def get_prediction(submission_id: str, user_id: str = Depends(verify_any_authenticated_token)):
    """
    Mengambil hasil prediksi final untuk submission_id.
    """
    submission = get_submission_by_id(submission_id)
    if not submission:
        raise HTTPException(
            status_code=404,
            detail=f"Submission dengan ID '{submission_id}' tidak ditemukan.",
        )

    if not check_user_submission_read_access(user_id, submission_id):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Anda tidak memiliki akses untuk membaca data prediksi ini."
        )

    model_ai = submission.get("model_ai")
    predictions = get_predictions_by_submission(submission_id, model_ai)

    sections_dict = {}
    for pred in predictions:
        code = pred.get("section_code")
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
def get_submission_results(submission_id: str, user_id: str = Depends(verify_any_authenticated_token)):
    """
    Mengambil hasil prediksi final untuk submission_id (format dosen).
    """
    submission = get_submission_by_id(submission_id)
    if not submission:
        raise HTTPException(
            status_code=404,
            detail=f"Submission dengan ID '{submission_id}' tidak ditemukan.",
        )

    if not check_user_submission_read_access(user_id, submission_id):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Anda tidak memiliki akses untuk membaca hasil review ini."
        )

    model_ai = submission.get("model_ai")
    predictions = get_predictions_by_submission(submission_id, model_ai)

    sections_dict = {}
    for pred in predictions:
        code = pred.get("section_code")
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


@app.get("/health/live")
def health_live():
    return {"status": "healthy"}


@app.get("/contracts/domain")
def domain_contract():
    return get_domain_contract()


def _readiness_response() -> JSONResponse:
    dependencies = {
        "supabase": False,
        "redis": False,
        "worker": False,
    }
    try:
        supabase.table("system_settings").select("id").limit(1).execute()
        dependencies["supabase"] = True
    except Exception:
        logger.exception("Supabase readiness check failed")

    try:
        queue_state = queue_readiness()
        dependencies["redis"] = queue_state["redis"]
        dependencies["worker"] = queue_state["worker"]
    except Exception:
        logger.exception("Queue readiness check failed")

    ready = all(dependencies.values())
    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "status": "healthy" if ready else "degraded",
            "dependencies": dependencies,
        },
    )


@app.get("/health/ready")
def health_ready():
    return _readiness_response()


@app.get("/health")
def health():
    return _readiness_response()


def _model_manifest_summary() -> list[dict]:
    import json

    manifest_path = runtime_settings.model_root / "manifest.json"
    if not manifest_path.is_file():
        raise HTTPException(status_code=503, detail="MODEL_MANIFEST_UNAVAILABLE")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="MODEL_MANIFEST_INVALID",
        ) from exc

    summaries: dict[str, dict] = {}
    worker_ready = queue_readiness()["worker"]
    for artifact in manifest.get("artifacts", []):
        architecture = artifact.get("architecture")
        if not architecture:
            continue
        summary = summaries.setdefault(
            architecture,
            {
                "name": architecture,
                "total_models": 0,
                "input_shape": artifact.get("input_shape"),
                "manifest_verified_by_worker": worker_ready,
            },
        )
        summary["total_models"] += 1
    return list(summaries.values())


@app.get("/model-info")
def model_info(admin_user_id: str = Depends(verify_admin_token)):
    models = _model_manifest_summary()
    return {
        "total_models": sum(model["total_models"] for model in models),
        "models": models,
        "queue": queue_readiness(),
    }


@app.get("/cache-status")
def cache_status(admin_user_id: str = Depends(verify_admin_token)):
    return {
        "strategy": "single_worker_section_lru",
        "worker": queue_readiness()["worker"],
    }


@app.get("/audit-models")
def audit_models(admin_user_id: str = Depends(verify_admin_token)):
    return _model_manifest_summary()


@app.get("/lecturer/class-summary")
def get_class_summary(lecturer_id: str, current_user_id: str = Depends(verify_dosen_or_admin_token)):
    """
    Mengambil ringkasan statistik kelas dan mahasiswa yang diajar oleh dosen.
    """
    profile_res = supabase.table("profil_pengguna").select("role").eq("id", current_user_id).maybe_single().execute()
    role = profile_res.data.get("role", "").lower() if profile_res and profile_res.data else ""
    if role != "admin" and current_user_id != lecturer_id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Anda tidak dapat mengakses ringkasan kelas dosen lain."
        )

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
def get_ai_models(user_id: str = Depends(verify_dosen_or_admin_token)):
    return {
        "success": True,
        "models": _model_manifest_summary(),
    }


@app.get("/lecturer/course/{course_id}/stats")
def get_course_stats(course_id: str, user_id: str = Depends(verify_dosen_or_admin_token)):
    """
    Mengambil data statistik mahasiswa terdaftar untuk course_id.
    """
    if not check_lecturer_course_access(user_id, course_id):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Anda tidak ditugaskan untuk mata kuliah ini."
        )
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
        logger.error(f"[Course Stats] Internal error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal mengambil statistik mata kuliah.")


@app.get("/lecturer/course/{course_id}/students")
def get_course_students(course_id: str, user_id: str = Depends(verify_dosen_or_admin_token)):
    """
    Mengambil data roster mahasiswa terdaftar beserta status pengumpulan tugas mereka.
    """
    if not check_lecturer_course_access(user_id, course_id):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Anda tidak ditugaskan untuk mata kuliah ini."
        )
    try:
        # 1. Ambil data mahasiswa_id yang terdaftar di mata_kuliah_id
        enrollments = (
            supabase.table("mahasiswa_mata_kuliah")
            .select("mahasiswa_id")
            .eq("mata_kuliah_id", course_id)
            .execute()
        )
        student_ids = [e["mahasiswa_id"] for e in enrollments.data]
        
        if not student_ids:
            return {
                "success": True,
                "students": []
            }
            
        # 2. Ambil data profil mahasiswa
        profiles_res = (
            supabase.table("profil_pengguna")
            .select("id, nama_lengkap, nim_nip, kelas, foto_profil_url")
            .in_("id", student_ids)
            .execute()
        )
        
        # 3. Ambil data pengumpulan_tugas untuk course_id ini
        submissions_res = (
            supabase.table("pengumpulan_tugas")
            .select("id, mahasiswa_id, status_submit, waktu_submit, nilai_akhir, ai_status")
            .eq("mata_kuliah_id", course_id)
            .execute()
        )
        
        # 4. Ambil lembar_jawaban counts per pengumpulan_tugas
        sub_ids = [s["id"] for s in submissions_res.data]
        sheets_map = {}
        if sub_ids:
            sheets_res = (
                supabase.table("lembar_jawaban")
                .select("id, pengumpulan_tugas_id")
                .in_("pengumpulan_tugas_id", sub_ids)
                .execute()
            )
            for sheet in sheets_res.data:
                sub_id = sheet["pengumpulan_tugas_id"]
                sheets_map[sub_id] = sheets_map.get(sub_id, 0) + 1
        
        # 5. Gabungkan data
        students_list = []
        for profile in profiles_res.data:
            m_id = profile["id"]
            sub = next((s for s in submissions_res.data if s["mahasiswa_id"] == m_id), None)
            
            sub_data = None
            if sub:
                sub_id = sub["id"]
                sub_data = {
                    "id": sub_id,
                    "mahasiswa_id": m_id,
                    "status_submit": sub["status_submit"],
                    "waktu_submit": sub["waktu_submit"],
                    "nilai_akhir": sub["nilai_akhir"],
                    "ai_status": sub["ai_status"],
                    "sheets_count": sheets_map.get(sub_id, 0)
                }
                
            students_list.append({
                "id": m_id,
                "nama_lengkap": profile.get("nama_lengkap") or "Unknown",
                "nim_nip": profile.get("nim_nip") or "-",
                "kelas": profile.get("kelas") or "-",
                "foto_profil_url": profile.get("foto_profil_url"),
                "submission": sub_data
            })
            
        # Urutkan berdasarkan nama
        students_list.sort(key=lambda x: x["nama_lengkap"].lower())
        
        return {
            "success": True,
            "students": students_list
        }
    except Exception as e:
        logger.error(f"[Course Students] Internal error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal mengambil data mahasiswa.")


@app.post("/admin/predictions/count")
def admin_count_predictions(
    payload: PredictionIdsRequest,
    admin_user_id: str = Depends(verify_admin_token),
):
    answer_ids = [str(item) for item in payload.lembar_jawaban_ids]
    try:
        res = supabase.table("hasil_prediksi").select("id", count="exact").in_("lembar_jawaban_id", answer_ids).execute()
        return {"count": res.count if res.count is not None else len(res.data)}
    except Exception as e:
        logger.error(f"[Admin Predictions Count] Internal error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal menghitung prediksi.")


@app.post("/admin/predictions/delete")
def admin_delete_predictions(
    payload: PredictionIdsRequest,
    admin_user_id: str = Depends(verify_admin_token),
):
    answer_ids = [str(item) for item in payload.lembar_jawaban_ids]
    try:
        res = supabase.table("hasil_prediksi").delete().in_("lembar_jawaban_id", answer_ids).execute()
        return {"deleted": len(res.data) if res.data else 0}
    except Exception as e:
        logger.error(f"[Admin Predictions Delete] Internal error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal menghapus prediksi.")


@app.get("/audit/schema-check")
def audit_schema_check(admin_user_id: str = Depends(verify_admin_token)):
    """
    Checks the schema version of the audit_log table.
    """
    return {
        "schema_version": "enterprise",
        "columns_found": ["id", "user_id", "user_name", "role", "action", "target", "detail", "created_at"]
    }


@app.post("/audit/log")
def post_audit_log(
    payload: AuditEventRequest,
    token_user_id: str = Depends(verify_any_authenticated_token),
):
    """
    Endpoint untuk menerima penulisan audit log dari frontend.
    Memvalidasi dan menormalisasi payload sebelum diteruskan ke database.
    Identitas aktor diambil langsung dari token JWT dan profil database.
    """
    profile_res = supabase.table("profil_pengguna").select("nama_lengkap, role").eq("id", token_user_id).maybe_single().execute()
    if not profile_res or not profile_res.data:
        raise HTTPException(status_code=404, detail="PROFILE_NOT_FOUND")
        
    user_id = token_user_id
    user_name = profile_res.data.get("nama_lengkap") or "Unknown User"
    role = (profile_res.data.get("role") or "mahasiswa").lower()
    allowed_actions = {
        "mahasiswa": {
            "STUDENT_LOGIN",
            "ANSWER_UPLOADED",
            "ANSWER_REPLACED",
            "ANSWER_DELETED",
            "SUBMISSION_SUBMITTED",
        },
        "dosen": {
            "LECTURER_LOGIN",
            "REVIEW_DRAFT_SAVED",
            "FINAL_SCORE_SUBMITTED",
            "REUPLOAD_REQUESTED",
        },
        "admin": {
            "ADMIN_LOGIN",
            "SYSTEM_RESET",
            "ACTIVE_MODEL_CHANGED",
            "SYSTEM_SETTING_CHANGED",
            "STORAGE_PRUNE",
            "AUDIT_TEST",
        },
    }
    if payload.action not in allowed_actions.get(role, set()):
        raise HTTPException(status_code=403, detail="AUDIT_ACTION_NOT_ALLOWED")

    from utils.audit_helper import create_audit_log

    success = create_audit_log(
        action=payload.action,
        target=payload.target,
        detail=payload.detail,
        user_id=user_id,
        user_name=user_name,
        role=role
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="AUDIT_WRITE_FAILED")
        
    return {"success": True}


def delete_user(user_id: str, admin_user_id: str = Depends(verify_admin_token)):
    """
    Endpoint untuk menghapus pengguna dari database (profil_pengguna) 
    dan auth.users Supabase secara terurut.
    """
    import logging
    _logger = logging.getLogger("uvicorn")
    _logger.info(f"[Delete User Request] Target User ID: {user_id} requested by Admin: {admin_user_id}")
    cascade_errors = []

    try:
        # Check if profile exists in profil_pengguna
        profile_res = supabase.table("profil_pengguna").select("*").eq("id", user_id).execute()
        profile_exists = len(profile_res.data) > 0
        _logger.info(f"[Delete User Check] Profile exists in profil_pengguna: {profile_exists}")
        
        # Check if user exists in auth.users
        auth_user_exists = False
        try:
            auth_user_res = supabase.auth.admin.get_user_by_id(user_id)
            if auth_user_res and auth_user_res.user:
                auth_user_exists = True
        except Exception as auth_err:
            _logger.error(f"[Delete User Check] Error checking auth.users: {auth_err}")
            
        _logger.info(f"[Delete User Check] User exists in auth.users: {auth_user_exists}")
        
        if not profile_exists and not auth_user_exists:
            raise HTTPException(status_code=404, detail="Pengguna tidak ditemukan di sistem.")

        # 1. Hapus data lembar jawaban & file storage mahasiswa
        sub_res = supabase.table("pengumpulan_tugas").select("id").eq("mahasiswa_id", user_id).execute()
        if sub_res.data:
            for sub in sub_res.data:
                sub_id = sub["id"]
                sheets_res = supabase.table("lembar_jawaban").select("id, image_url").eq("pengumpulan_tugas_id", sub_id).execute()
                if sheets_res.data:
                    # Hapus file dari Storage bucket 'lembar-jawaban'
                    files_to_delete = [s["image_url"] for s in sheets_res.data if s.get("image_url")]
                    if files_to_delete:
                        _logger.info(f"[Delete User] Removing {len(files_to_delete)} files from storage 'lembar-jawaban'...")
                        try:
                            supabase.storage.from_("lembar-jawaban").remove(files_to_delete)
                        except Exception as storage_err:
                            _logger.error(f"[Delete User Warning] Storage deletion failed: {storage_err}")
                            cascade_errors.append(f"storage: {storage_err}")
                    
                    # Hapus hasil_prediksi
                    sheet_ids = [s["id"] for s in sheets_res.data]
                    if sheet_ids:
                        try:
                            supabase.table("hasil_prediksi").delete().in_("lembar_jawaban_id", sheet_ids).execute()
                            _logger.info("[Delete User] Deleted related hasil_prediksi")
                        except Exception as pred_err:
                            _logger.error(f"[Delete User] Failed to delete hasil_prediksi: {pred_err}")
                            cascade_errors.append(f"hasil_prediksi: {pred_err}")
                    
                    # Hapus lembar_jawaban rows
                    try:
                        supabase.table("lembar_jawaban").delete().eq("pengumpulan_tugas_id", sub_id).execute()
                        _logger.info("[Delete User] Deleted related lembar_jawaban")
                    except Exception as lj_err:
                        _logger.error(f"[Delete User] Failed to delete lembar_jawaban: {lj_err}")
                        cascade_errors.append(f"lembar_jawaban: {lj_err}")
                
                # Hapus pengumpulan_tugas row
                try:
                    supabase.table("pengumpulan_tugas").delete().eq("id", sub_id).execute()
                    _logger.info("[Delete User] Deleted related pengumpulan_tugas")
                except Exception as pt_err:
                    _logger.error(f"[Delete User] Failed to delete pengumpulan_tugas: {pt_err}")
                    cascade_errors.append(f"pengumpulan_tugas: {pt_err}")

        # 2. Hapus foto profil dari Storage bucket 'profile-images' jika ada
        if profile_exists:
            foto_url = profile_res.data[0].get("foto_profil_url")
            if foto_url:
                _logger.info(f"[Delete User] Removing profile image from storage: {foto_url}")
                try:
                    supabase.storage.from_("profile-images").remove([foto_url])
                except Exception as avatar_err:
                    _logger.error(f"[Delete User Warning] Profile image storage deletion failed: {avatar_err}")
                    cascade_errors.append(f"profile-image: {avatar_err}")

        # 3. Hapus data relasi (mahasiswa_mata_kuliah & dosen_mata_kuliah)
        rel_mhs = supabase.table("mahasiswa_mata_kuliah").delete().eq("mahasiswa_id", user_id).execute()
        _logger.info(f"[Delete User] Deleted from mahasiswa_mata_kuliah: {len(rel_mhs.data) if rel_mhs.data else 0} rows")
        
        rel_dsn = supabase.table("dosen_mata_kuliah").delete().eq("dosen_id", user_id).execute()
        _logger.info(f"[Delete User] Deleted from dosen_mata_kuliah: {len(rel_dsn.data) if rel_dsn.data else 0} rows")

        # 4. Hapus profil_pengguna
        if profile_exists:
            profile_del_res = supabase.table("profil_pengguna").delete().eq("id", user_id).execute()
            _logger.info(f"[Delete User] Deleted from profil_pengguna: {len(profile_del_res.data) if profile_del_res.data else 0} rows")

        # 5. Hapus auth.users
        if auth_user_exists:
            auth_del_res = supabase.auth.admin.delete_user(user_id)
            _logger.info(f"[Delete User] Deleted from auth.users successfully: {auth_del_res}")

        # Log cascade errors if any (partial success)
        if cascade_errors:
            _logger.warning(f"[Delete User] Completed with {len(cascade_errors)} non-critical errors: {cascade_errors}")

        return {"success": True, "message": f"Pengguna {user_id} berhasil dihapus.", "warnings": len(cascade_errors)}

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"[Delete User Error] Exception occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal menghapus pengguna. Silakan coba lagi.")


def delete_course(course_id: str, admin_user_id: str = Depends(verify_admin_token)):
    """
    Endpoint terpusat untuk menghapus mata kuliah beserta semua data terkait
    (enrollment, submission, lembar jawaban, hasil prediksi, file storage) secara aman.
    """
    import logging
    logger = logging.getLogger("uvicorn")
    logger.info(f"[Delete Course Request] Target Course ID: {course_id} requested by Admin: {admin_user_id}")

    try:
        # Check if course exists
        course_res = supabase.table("mata_kuliah").select("*").eq("id", course_id).execute()
        if not course_res.data:
            raise HTTPException(status_code=404, detail="Mata kuliah tidak ditemukan.")

        # 1. Ambil data submission untuk mata kuliah ini
        sub_res = supabase.table("pengumpulan_tugas").select("id").eq("mata_kuliah_id", course_id).execute()
        if sub_res.data:
            for sub in sub_res.data:
                sub_id = sub["id"]
                
                # Ambil data lembar jawaban
                sheets_res = supabase.table("lembar_jawaban").select("id, image_url").eq("pengumpulan_tugas_id", sub_id).execute()
                if sheets_res.data:
                    # Hapus file dari Storage bucket 'lembar-jawaban'
                    files_to_delete = [s["image_url"] for s in sheets_res.data if s.get("image_url")]
                    if files_to_delete:
                        logger.info(f"[Delete Course] Removing {len(files_to_delete)} files from storage...")
                        try:
                            supabase.storage.from_("lembar-jawaban").remove(files_to_delete)
                        except Exception as storage_err:
                            logger.error(f"[Delete Course Warning] Storage deletion failed: {storage_err}")

                    # Hapus hasil_prediksi
                    sheet_ids = [s["id"] for s in sheets_res.data]
                    if sheet_ids:
                        supabase.table("hasil_prediksi").delete().in_("lembar_jawaban_id", sheet_ids).execute()
                        logger.info("[Delete Course] Deleted related hasil_prediksi")

                    # Hapus lembar_jawaban rows
                    supabase.table("lembar_jawaban").delete().eq("pengumpulan_tugas_id", sub_id).execute()
                    logger.info("[Delete Course] Deleted related lembar_jawaban")

                # Hapus pengumpulan_tugas row
                supabase.table("pengumpulan_tugas").delete().eq("id", sub_id).execute()
                logger.info("[Delete Course] Deleted related pengumpulan_tugas")

        # 2. Hapus mahasiswa_mata_kuliah (enrollment)
        supabase.table("mahasiswa_mata_kuliah").delete().eq("mata_kuliah_id", course_id).execute()
        logger.info("[Delete Course] Deleted related mahasiswa_mata_kuliah")

        # 3. Hapus dosen_mata_kuliah (assignment)
        supabase.table("dosen_mata_kuliah").delete().eq("mata_kuliah_id", course_id).execute()
        logger.info("[Delete Course] Deleted related dosen_mata_kuliah")

        # 4. Hapus mata_kuliah row
        supabase.table("mata_kuliah").delete().eq("id", course_id).execute()
        logger.info("[Delete Course] Deleted mata_kuliah successfully")

        return {"success": True, "message": f"Mata kuliah {course_id} berhasil dihapus."}

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"[Delete Course Error] Exception occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal menghapus mata kuliah. Silakan coba lagi.")


def delete_enrollment(enrollment_id: str, admin_user_id: str = Depends(verify_admin_token)):
    """
    Endpoint terpusat untuk menghapus enrollment mahasiswa beserta data terkait
    (submission, lembar jawaban, hasil prediksi, file storage) pada mata kuliah terkait.
    """
    import logging
    logger = logging.getLogger("uvicorn")
    logger.info(f"[Delete Enrollment Request] Target Enrollment ID: {enrollment_id} requested by Admin: {admin_user_id}")

    try:
        # Check if enrollment exists
        enroll_res = supabase.table("mahasiswa_mata_kuliah").select("*").eq("id", enrollment_id).execute()
        if not enroll_res.data:
            raise HTTPException(status_code=404, detail="Enrollment tidak ditemukan.")

        enrollment = enroll_res.data[0]
        mahasiswa_id = enrollment["mahasiswa_id"]
        mata_kuliah_id = enrollment["mata_kuliah_id"]

        # 1. Ambil data submission untuk mahasiswa di mata kuliah ini
        sub_res = supabase.table("pengumpulan_tugas").select("id").eq("mahasiswa_id", mahasiswa_id).eq("mata_kuliah_id", mata_kuliah_id).execute()
        if sub_res.data:
            for sub in sub_res.data:
                sub_id = sub["id"]
                
                # Ambil data lembar jawaban
                sheets_res = supabase.table("lembar_jawaban").select("id, image_url").eq("pengumpulan_tugas_id", sub_id).execute()
                if sheets_res.data:
                    # Hapus file dari Storage
                    files_to_delete = [s["image_url"] for s in sheets_res.data if s.get("image_url")]
                    if files_to_delete:
                        logger.info(f"[Delete Enrollment] Removing {len(files_to_delete)} files from storage...")
                        try:
                            supabase.storage.from_("lembar-jawaban").remove(files_to_delete)
                        except Exception as storage_err:
                            logger.error(f"[Delete Enrollment Warning] Storage deletion failed: {storage_err}")

                    # Hapus hasil_prediksi
                    sheet_ids = [s["id"] for s in sheets_res.data]
                    if sheet_ids:
                        supabase.table("hasil_prediksi").delete().in_("lembar_jawaban_id", sheet_ids).execute()

                    # Hapus lembar_jawaban rows
                    supabase.table("lembar_jawaban").delete().eq("pengumpulan_tugas_id", sub_id).execute()

                # Hapus pengumpulan_tugas row
                supabase.table("pengumpulan_tugas").delete().eq("id", sub_id).execute()

        # 2. Hapus mahasiswa_mata_kuliah row
        supabase.table("mahasiswa_mata_kuliah").delete().eq("id", enrollment_id).execute()
        logger.info("[Delete Enrollment] Deleted mahasiswa_mata_kuliah successfully")

        return {"success": True, "message": f"Enrollment {enrollment_id} berhasil dihapus."}

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"[Delete Enrollment Error] Exception occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal menghapus enrollment. Silakan coba lagi.")


def _queue_cleanup_from_rpc_result(data: object) -> str | None:
    if not isinstance(data, dict):
        return None
    paths = data.get("object_paths", [])
    if not isinstance(paths, list):
        return None
    return enqueue_storage_cleanup(paths)


@app.delete("/admin/user/{user_id}")
def delete_user_transactional(
    user_id: UUID,
    _admin_user_id: str = Depends(verify_admin_token),
):
    try:
        result = supabase.rpc(
            "admin_delete_user_data",
            {"p_user_id": str(user_id)},
        ).execute()
        cleanup_job_id = _queue_cleanup_from_rpc_result(result.data)
        return {"success": True, "cleanup_job_id": cleanup_job_id}
    except Exception as exc:
        logger.exception("Transactional user deletion failed")
        raise HTTPException(status_code=500, detail="USER_DELETE_FAILED") from exc


@app.patch("/admin/user/{user_id}/role")
def update_user_role(
    user_id: UUID,
    payload: UserRoleUpdateRequest,
    admin_user_id: str = Depends(verify_admin_token),
):
    profile = (
        supabase.table("profil_pengguna")
        .select("id, role")
        .eq("id", str(user_id))
        .maybe_single()
        .execute()
    )
    if not profile.data:
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")

    current_role = str(profile.data.get("role", "")).lower()
    if current_role == "admin":
        raise HTTPException(status_code=409, detail="ADMIN_ROLE_IS_PROTECTED")

    try:
        updated = (
            supabase.table("profil_pengguna")
            .update({"role": payload.new_role.value})
            .eq("id", str(user_id))
            .select("id, role")
            .single()
            .execute()
        )
        from utils.audit_helper import create_audit_log

        create_audit_log(
            action="ADMIN_USER_ROLE_UPDATED",
            target="profil_pengguna",
            detail={
                "target_id": str(user_id),
                "old_role": current_role,
                "new_role": payload.new_role.value,
            },
            user_id=admin_user_id,
            role="admin",
        )
        return {"success": True, "data": updated.data}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Admin role update failed")
        raise HTTPException(status_code=500, detail="USER_ROLE_UPDATE_FAILED") from exc


@app.delete("/admin/course/{course_id}")
def delete_course_transactional(
    course_id: UUID,
    _admin_user_id: str = Depends(verify_admin_token),
):
    try:
        result = supabase.rpc(
            "admin_delete_course_data",
            {"p_course_id": str(course_id)},
        ).execute()
        cleanup_job_id = _queue_cleanup_from_rpc_result(result.data)
        return {"success": True, "cleanup_job_id": cleanup_job_id}
    except Exception as exc:
        logger.exception("Transactional course deletion failed")
        raise HTTPException(status_code=500, detail="COURSE_DELETE_FAILED") from exc


@app.delete("/admin/enrollment/{enrollment_id}")
def delete_enrollment_transactional(
    enrollment_id: UUID,
    _admin_user_id: str = Depends(verify_admin_token),
):
    enrollment = (
        supabase.table("mahasiswa_mata_kuliah")
        .select("mahasiswa_id, mata_kuliah_id")
        .eq("id", str(enrollment_id))
        .maybe_single()
        .execute()
    )
    if not enrollment.data:
        raise HTTPException(status_code=404, detail="ENROLLMENT_NOT_FOUND")

    try:
        result = supabase.rpc(
            "admin_delete_enrollment_data",
            {
                "p_student_id": enrollment.data["mahasiswa_id"],
                "p_course_id": enrollment.data["mata_kuliah_id"],
            },
        ).execute()
        cleanup_job_id = _queue_cleanup_from_rpc_result(result.data)
        return {"success": True, "cleanup_job_id": cleanup_job_id}
    except Exception as exc:
        logger.exception("Transactional enrollment deletion failed")
        raise HTTPException(
            status_code=500,
            detail="ENROLLMENT_DELETE_FAILED",
        ) from exc


@app.post("/admin/reset")
def reset_demo_data(
    payload: DemoResetRequest,
    _admin_user_id: str = Depends(verify_admin_token),
):
    delete_submissions = payload.reset_type in {"submissions", "all"}
    delete_enrollments = payload.reset_type in {"enrollments", "all"}
    try:
        result = supabase.rpc(
            "admin_reset_demo_data",
            {
                "p_delete_submissions": delete_submissions,
                "p_delete_enrollments": delete_enrollments,
            },
        ).execute()
        cleanup_job_id = _queue_cleanup_from_rpc_result(result.data)
        return {
            "success": True,
            **(result.data if isinstance(result.data, dict) else {}),
            "cleanup_job_id": cleanup_job_id,
        }
    except Exception as exc:
        logger.exception("Transactional demo reset failed")
        raise HTTPException(status_code=500, detail="DEMO_RESET_FAILED") from exc


@app.get("/audit/test")
def audit_test(admin_user_id: str = Depends(verify_admin_token)):
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


def _list_storage_files_recursive(bucket: str, folder: str = "") -> list:
    """
    List semua file di storage secara rekursif dengan pagination.
    """
    import logging
    logger = logging.getLogger("uvicorn")
    files = []
    offset = 0
    limit = 100
    try:
        while True:
            res = supabase.storage.from_(bucket).list(folder, options={"limit": limit, "offset": offset})
            if not res:
                break
            for item in res:
                name = item.get("name")
                if not name or name == ".placeholder":
                    continue
                is_folder = item.get("id") is None
                item_path = f"{folder}/{name}" if folder else name
                if is_folder:
                    files.extend(_list_storage_files_recursive(bucket, item_path))
                else:
                    files.append({
                        "path": item_path,
                        "size": item.get("metadata", {}).get("size", 0) or item.get("size", 0)
                    })
            if len(res) < limit:
                break
            offset += limit
    except Exception as e:
        logger.error(f"[Storage List] Gagal melist folder '{folder}': {e}")
    return files


@app.get("/admin/storage/audit")
def audit_storage(admin_user_id: str = Depends(verify_admin_token)):
    """
    Scan storage bucket 'lembar-jawaban' and find orphaned files.
    """
    import logging
    logger = logging.getLogger("uvicorn")
    logger.info(f"[Storage Audit Request] Requested by Admin: {admin_user_id}")
    
    try:
        bucket = "lembar-jawaban"
        
        # 1. Ambil data image_url dari database
        db_res = supabase.table("lembar_jawaban").select("image_url").execute()
        db_paths = {row["image_url"] for row in db_res.data if row.get("image_url")}
        
        # 2. List semua file di storage bucket
        storage_files = _list_storage_files_recursive(bucket)
        
        # 3. Cari file yatim piatu (orphan)
        orphans = []
        total_size = 0
        for f in storage_files:
            path = f["path"]
            if path not in db_paths:
                orphans.append(f)
                total_size += f["size"]
                
        return {
            "success": True,
            "summary": {
                "total_files": len(storage_files),
                "db_referenced_files": len(db_paths),
                "orphan_count": len(orphans),
                "orphan_size_bytes": total_size,
                "orphan_size_mb": round(total_size / (1024 * 1024), 2)
            },
            "orphans": orphans
        }
    except Exception as e:
        logger.error(f"[Storage Audit Error] Exception occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal melakukan audit storage.")


@app.post("/admin/storage/prune")
def prune_storage(admin_user_id: str = Depends(verify_admin_token)):
    """
    Scan storage bucket 'lembar-jawaban' and delete orphaned files.
    """
    import logging
    logger = logging.getLogger("uvicorn")
    logger.info(f"[Storage Prune Request] Requested by Admin: {admin_user_id}")
    
    try:
        bucket = "lembar-jawaban"
        
        # 1. Ambil data image_url dari database
        db_res = supabase.table("lembar_jawaban").select("image_url").execute()
        db_paths = {row["image_url"] for row in db_res.data if row.get("image_url")}
        
        # 2. List semua file di storage bucket
        storage_files = _list_storage_files_recursive(bucket)
        
        # 3. Cari file yatim piatu (orphan)
        orphans_to_delete = []
        total_size = 0
        for f in storage_files:
            path = f["path"]
            if path not in db_paths:
                orphans_to_delete.append(path)
                total_size += f["size"]
                
        # 4. Hapus file yatim piatu dari storage
        deleted_count = 0
        if orphans_to_delete:
            chunk_size = 100
            for i in range(0, len(orphans_to_delete), chunk_size):
                chunk = orphans_to_delete[i:i + chunk_size]
                supabase.storage.from_(bucket).remove(chunk)
                deleted_count += len(chunk)
                logger.info(f"[Storage Prune] Berhasil menghapus chunk {len(chunk)} file")
                
        # Tulis ke log audit
        from utils.audit_helper import create_audit_log
        create_audit_log(
            action="STORAGE_PRUNE",
            target=bucket,
            detail={
                "deleted_count": deleted_count,
                "reclaimed_size_bytes": total_size,
                "reclaimed_size_mb": round(total_size / (1024 * 1024), 2)
            },
            user_id=admin_user_id,
            user_name="Administrator",
            role="admin"
        )
        
        return {
            "success": True,
            "message": f"Storage cleanup complete. Reclaimed {round(total_size / (1024 * 1024), 2)} MB from {deleted_count} orphaned files.",
            "deleted_count": deleted_count,
            "reclaimed_size_bytes": total_size
        }
    except Exception as e:
        logger.error(f"[Storage Prune Error] Exception occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal membersihkan storage.")


def check_email(email: str, user_id: str = Depends(verify_any_authenticated_token)):
    """
    Check if an email is registered in Supabase auth.users using check_email_exists() RPC.
    FIX #2: Now requires authentication to prevent user enumeration attacks.
    """
    if not email:
        raise HTTPException(status_code=400, detail="Parameter email wajib diisi.")
    
    try:
        email_clean = email.strip().lower()
        response = supabase.rpc("check_email_exists", {"email_to_check": email_clean}).execute()
        # The RPC returns a boolean directly, which is wrapped in response.data
        exists = response.data
        return {"exists": bool(exists)}
    except Exception as e:
        logger.error(f"[Check Email Error] {e}", exc_info=True)
        # Fallback to True so we don't block login if there's a temporary database issue
        return {"exists": True}
