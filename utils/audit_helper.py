import json
from utils.supabase_client import get_service_client

def standardize_model_name(name: str) -> str:
    """
    Standardize model name to 'DenseNet121' as per user requirements.
    """
    if not name:
        return name
    name = name.replace("DenseNet201", "DenseNet121")
    name = name.replace("DenseNet-121", "DenseNet121")
    name = name.replace("Dense Net 121", "DenseNet121")
    return name


def create_audit_log(
    action: str,
    target: str,
    detail: any,
    user_id: str = None,
    user_name: str = None,
    role: str = None
) -> bool:
    """
    Centrally log events in a non-blocking way using the standardized enterprise schema.
    Returns True if log insertion succeeded, otherwise False.
    """
    try:
        # Standardisasi hanya diterapkan pada detail payload.
        # `action` dan `target` adalah domain audit, bukan nama model.
        if isinstance(detail, str):
            detail = standardize_model_name(detail)
        elif isinstance(detail, dict):
            detail_str = json.dumps(detail)
            detail_str = standardize_model_name(detail_str)
            try:
                detail = json.loads(detail_str)
            except Exception:
                detail = detail_str

        # Resolve actor attributes
        if not role:
            role = "dosen"
        if not user_name:
            user_name = "Dosen"

        payload = {
            "user_id": user_id,
            "user_name": user_name,
            "role": role,
            "action": action,
            "target": target,
            "detail": detail
        }
        
        service_client = get_service_client()
        service_client.table("audit_log").insert(payload).execute()
        return True
    except Exception as db_err:
        from utils.logging_helper import logger
        logger.error(f"[AUDIT ERROR] Failed to write audit log: {db_err}", exc_info=True)
        return False
