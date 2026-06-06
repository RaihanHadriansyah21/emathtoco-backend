import os
import json
import traceback
from utils.supabase_client import supabase

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

_HAS_ENTERPRISE_SCHEMA = None

def check_enterprise_schema() -> bool:
    """
    Checks if the enterprise schema is active.
    Caches the result to prevent repeated database query errors.
    """
    global _HAS_ENTERPRISE_SCHEMA
    if _HAS_ENTERPRISE_SCHEMA is not None:
        return _HAS_ENTERPRISE_SCHEMA
    try:
        # Check if user_id column exists
        supabase.table("audit_log").select("user_id").limit(0).execute()
        _HAS_ENTERPRISE_SCHEMA = True
    except Exception as e:
        err_msg = str(e).lower()
        if "column" in err_msg or "undefined_column" in err_msg or "42703" in err_msg:
            _HAS_ENTERPRISE_SCHEMA = False
        else:
            # For connection/network issues, do not cache permanently
            return False
    return _HAS_ENTERPRISE_SCHEMA

def create_audit_log(
    action: str,
    target: str,
    detail: any,
    user_id: str = None,
    user_name: str = None,
    role: str = None
) -> bool:
    """
    Centrally log events in a non-blocking way.
    Supports both new schema and old schema via dynamic schema detection.
    Returns True if log insertion succeeded, otherwise False.
    """
    try:
        # Standardize model name
        action = standardize_model_name(action)
        target = standardize_model_name(target)
        
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

        description_text = json.dumps(detail, indent=2) if isinstance(detail, (dict, list)) else str(detail)

        has_enterprise = check_enterprise_schema()

        if has_enterprise:
            payload = {
                "user_id": user_id,
                "user_name": user_name,
                "role": role,
                "action": action,
                "target": target,
                "detail": detail,
                # Write to legacy columns as well for 100% backward compatibility
                "actor_id": user_id,
                "actor_role": role,
                "action_type": action,
                "target_type": target,
                "description": description_text
            }
            try:
                supabase.table("audit_log").insert(payload).execute()
                print(f"[AUDIT] action={action} role={role} target={target} success=True")
                return True
            except Exception as db_err:
                err_msg = str(db_err)
                print(f"[AUDIT] action={action} role={role} target={target} success=False")
                print(f"[AUDIT] [ERROR] code=DB_INSERT_FAILED msg={err_msg}")
                print(f"[AUDIT] [PAYLOAD] {payload}")
                
                # Retry legacy fallback insert
                fallback_payload = {
                    "actor_id": user_id,
                    "actor_role": role,
                    "action_type": action,
                    "target_type": target,
                    "description": description_text
                }
                try:
                    supabase.table("audit_log").insert(fallback_payload).execute()
                    print(f"[AUDIT] Fallback log insertion success=True")
                    return True
                except Exception as fb_err:
                    fb_msg = str(fb_err)
                    print(f"[AUDIT] Fallback log insertion success=False")
                    print(f"[AUDIT] [ERROR] code=FALLBACK_FAILED msg={fb_msg}")
                    print(f"[AUDIT] [PAYLOAD] {fallback_payload}")
                    return False
        else:
            payload = {
                "actor_id": user_id,
                "actor_role": role,
                "action_type": action,
                "target_type": target,
                "description": description_text
            }
            try:
                supabase.table("audit_log").insert(payload).execute()
                print(f"[AUDIT] action={action} role={role} target={target} success=True")
                return True
            except Exception as db_err:
                err_msg = str(db_err)
                print(f"[AUDIT] action={action} role={role} target={target} success=False")
                print(f"[AUDIT] [ERROR] code=DB_LEGACY_INSERT_FAILED msg={err_msg}")
                print(f"[AUDIT] [PAYLOAD] {payload}")
                return False
    except Exception as e:
        # Non-blocking: only print to console, never crash application
        print(f"[AUDIT] Central logger exception: {e}")
        traceback.print_exc()
        return False
