import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL:
    print("CRITICAL ERROR: 'SUPABASE_URL' is missing or empty in .env", file=sys.stderr)
    raise ValueError("Environment variable 'SUPABASE_URL' is required but not set.")

if not SUPABASE_KEY:
    print("CRITICAL ERROR: 'SUPABASE_SERVICE_ROLE_KEY' is missing or empty in .env", file=sys.stderr)
    raise ValueError("Environment variable 'SUPABASE_SERVICE_ROLE_KEY' is required but not set.")

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"CRITICAL ERROR: Failed to initialize Supabase client: {e}", file=sys.stderr)
    raise

# ── Cached service client for admin operations ──────────────────
# Avoids creating a new client per-call while staying isolated
# from token pollution. Reset if it somehow gets polluted.
_service_client = None

def get_service_client():
    """
    Returns a cached, unpolluted Supabase client instance initialized with the service role key.
    Use this for admin operations to avoid RLS violations caused by token pollution.
    """
    global _service_client
    if _service_client is None:
        _service_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _service_client


def verify_user_token(token: str):
    """
    Verify a JWT token using a FRESH Supabase client to avoid polluting
    the global singleton's auth context.

    supabase.auth.get_user(token) internally injects the token into
    the client's default Authorization header. If called on the global
    singleton, all subsequent table operations would run as that user
    instead of service_role — breaking RLS.

    Returns:
        The user object if verification succeeds.
    Raises:
        Exception if the token is invalid or expired.
    """
    fresh_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    user_res = fresh_client.auth.get_user(token)
    if not user_res or not user_res.user:
        return None
    return user_res.user

