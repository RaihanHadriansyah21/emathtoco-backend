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
