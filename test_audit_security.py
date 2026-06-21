import os
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from backend
backend_env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(backend_env_path)

supabase_url = os.environ.get("SUPABASE_URL")
service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

print("==================================================================")
print("EMATHTOCO — SECURITY PROOF TEST SUITE")
print("==================================================================")
print(f"Supabase URL: {supabase_url}")

# Initialize admin client
supabase_admin: Client = create_client(supabase_url, service_key)

users_to_test = {
    "mahasiswa": {
        "email": "mhs12@gmail.com",
        "id": "d6db9404-32a6-4fd6-8ccf-a7cdcac47641"
    },
    "dosen": {
        "email": "pakgelarbudiman@emathtoco.com",
        "id": "aa36f617-857c-400a-ae85-444b4284e2da"
    },
    "admin": {
        "email": "emathtoco@gmail.com",
        "id": "eb34d26b-76d9-4b9f-b43a-7f635bf2fc00"
    }
}

new_password = "password123"

# 1. Reset passwords
print("\n=== STEP 1: RESETTING TEST PASSWORDS TO password123 ===")
for role, uinfo in users_to_test.items():
    uid = uinfo["id"]
    email = uinfo["email"]
    try:
        try:
            supabase_admin.auth.admin.update_user_by_id(uid, {"password": new_password})
            print(f"[OK] Reset password for {role} ({email})")
        except Exception:
            supabase_admin.auth.admin.update_user_by_id(user_id=uid, attributes={"password": new_password})
            print(f"[OK] Reset password for {role} ({email})")
    except Exception as e:
        print(f"[ERROR] Failed to reset password for {role} ({email}): {e}")

# 2. Authenticate and get user clients / tokens
print("\n=== STEP 2: AUTHENTICATING AND OBTAINING ACCESS TOKENS ===")
tokens = {}
for role, uinfo in users_to_test.items():
    email = uinfo["email"]
    try:
        res = supabase_admin.auth.sign_in_with_password({"email": email, "password": new_password})
        tokens[role] = res.session.access_token
        print(f"[OK] Authenticated as {role} ({email}), token obtained.")
    except Exception as e:
        print(f"[ERROR] Failed to authenticate as {role} ({email}): {e}")

# 3. Test Cases
backend_url = "http://127.0.0.1:8000"
anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhreHhoYWN0cHdpcWR6ZWNyYnh3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE2ODUwNTEsImV4cCI6MjA5NzI2MTA1MX0.5VjFJiFzK0aj-zwQFi_1QmPKrrrX7_P6eFB56ADJlGc"

print("\n=== STEP 3: RUNNING SECURITY PROOF CASES ===")

# CASE 1: Mahasiswa sends spoofed user_name & role to backend
if "mahasiswa" in tokens:
    print("\n--- CASE 1: Mahasiswa spoofing attempt ---")
    headers = {"Authorization": f"Bearer {tokens['mahasiswa']}"}
    spoofed_payload = {
        "action": "STUDENT_LOGIN",
        "target": "profil_pengguna",
        "details": {"role": "mahasiswa"},
        "user_name": "Admin Utama",
        "role": "admin",
        "user_id": "eb34d26b-76d9-4b9f-b43a-7f635bf2fc00"
    }
    try:
        res = requests.post(f"{backend_url}/audit/log", json=spoofed_payload, headers=headers)
        print(f"Backend POST status: {res.status_code}, response: {res.text}")
        
        audit_res = supabase_admin.table("audit_log").select("*").order("created_at", desc=True).limit(1).execute()
        if audit_res.data:
            latest_log = audit_res.data[0]
            print(f"Latest audit log stored:")
            print(f"  action:    {latest_log.get('action')}")
            print(f"  user_id:   {latest_log.get('user_id')}")
            print(f"  user_name: {latest_log.get('user_name')}")
            print(f"  role:      {latest_log.get('role')}")
            
            assert latest_log.get("user_id") == users_to_test["mahasiswa"]["id"], "Spoofing failed: user_id was spoofed!"
            assert latest_log.get("user_name") != "Admin Utama", "Spoofing failed: user_name was spoofed!"
            assert latest_log.get("role") == "mahasiswa", "Spoofing failed: role was spoofed!"
            print("RESULT: CASE 1 PASS")
        else:
            print("RESULT: CASE 1 FAILED (No audit log found)")
    except Exception as e:
        print(f"[ERROR] Case 1 exception: {e}")

# CASE 2: Dosen sends spoofed user_name
if "dosen" in tokens:
    print("\n--- CASE 2: Dosen spoofing attempt ---")
    headers = {"Authorization": f"Bearer {tokens['dosen']}"}
    spoofed_payload = {
        "action": "LECTURER_LOGIN",
        "target": "auth",
        "details": {"role": "dosen"},
        "user_name": "Super Admin"
    }
    try:
        res = requests.post(f"{backend_url}/audit/log", json=spoofed_payload, headers=headers)
        print(f"Backend POST status: {res.status_code}, response: {res.text}")
        
        audit_res = supabase_admin.table("audit_log").select("*").order("created_at", desc=True).limit(1).execute()
        if audit_res.data:
            latest_log = audit_res.data[0]
            print(f"Latest audit log stored:")
            print(f"  action:    {latest_log.get('action')}")
            print(f"  user_id:   {latest_log.get('user_id')}")
            print(f"  user_name: {latest_log.get('user_name')}")
            print(f"  role:      {latest_log.get('role')}")
            
            assert latest_log.get("user_name") != "Super Admin", "Spoofing failed: user_name was spoofed!"
            print("RESULT: CASE 2 PASS")
        else:
            print("RESULT: CASE 2 FAILED (No audit log found)")
    except Exception as e:
        print(f"[ERROR] Case 2 exception: {e}")

# CASE 3: Mahasiswa query supabase.from("audit_log").select("*")
if "mahasiswa" in tokens:
    print("\n--- CASE 3: Mahasiswa RLS Read Check ---")
    client_mhs = create_client(supabase_url, anon_key)
    client_mhs.postgrest.auth(tokens["mahasiswa"])
    try:
        res = client_mhs.table("audit_log").select("*").execute()
        print(f"Mahasiswa select result length: {len(res.data) if res.data else 0}")
        if res.data and len(res.data) > 0:
            print("RESULT: CASE 3 FAIL (Read was allowed)")
        else:
            print("RESULT: CASE 3 PASS (No read access)")
    except Exception as e:
        err_str = str(e)
        print(f"Mahasiswa read threw error as expected: {err_str}")
        if "permission denied" in err_str.lower() or "42501" in err_str.lower():
            print("RESULT: CASE 3 PASS")
        else:
            print("RESULT: CASE 3 FAIL (Unexpected error)")

# CASE 4: Dosen query supabase.from("audit_log").select("*")
if "dosen" in tokens:
    print("\n--- CASE 4: Dosen RLS Read Check ---")
    client_dosen = create_client(supabase_url, anon_key)
    client_dosen.postgrest.auth(tokens["dosen"])
    try:
        res = client_dosen.table("audit_log").select("*").execute()
        print(f"Dosen select result length: {len(res.data) if res.data else 0}")
        if res.data and len(res.data) > 0:
            print("RESULT: CASE 4 FAIL (Read was allowed)")
        else:
            print("RESULT: CASE 4 PASS (No read access)")
    except Exception as e:
        err_str = str(e)
        print(f"Dosen read threw error as expected: {err_str}")
        if "permission denied" in err_str.lower() or "42501" in err_str.lower():
            print("RESULT: CASE 4 PASS")
        else:
            print("RESULT: CASE 4 FAIL (Unexpected error)")

# CASE 5: Admin query supabase.from("audit_log").select("*")
if "admin" in tokens:
    print("\n--- CASE 5: Admin RLS Read Check ---")
    client_admin = create_client(supabase_url, anon_key)
    client_admin.postgrest.auth(tokens["admin"])
    try:
        res = client_admin.table("audit_log").select("*").execute()
        print(f"Admin select result length: {len(res.data) if res.data else 0}")
        print("RESULT: CASE 5 PASS")
    except Exception as e:
        print(f"[ERROR] Admin read failed: {e}")
        print("RESULT: CASE 5 FAIL")
