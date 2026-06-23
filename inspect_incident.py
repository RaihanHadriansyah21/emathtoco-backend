import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhreHhoYWN0cHdpcWR6ZWNyYnh3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE2ODUwNTEsImV4cCI6MjA5NzI2MTA1MX0.5VjFJiFzK0aj-zwQFi_1QmPKrrrX7_P6eFB56ADJlGc"

if not supabase_url or not service_key:
    print("Missing env variables")
    sys.exit(1)

supabase_admin: Client = create_client(supabase_url, service_key)

email = "mhs12@gmail.com"
password = "password123"

print("Authenticating as mahasiswa...")
try:
    auth_res = supabase_admin.auth.sign_in_with_password({"email": email, "password": password})
    mhs_token = auth_res.session.access_token
    mhs_id = auth_res.user.id
    print(f"Mahasiswa ID: {mhs_id}")
except Exception as e:
    print("Auth failed:", e)
    sys.exit(1)

# Get an active course ID
res_mk = supabase_admin.table("mata_kuliah").select("id").limit(1).execute()
matkul_id = res_mk.data[0]['id'] if res_mk.data else None
print(f"Course ID to use: {matkul_id}")

# Create client as authenticated mahasiswa
supabase_mhs = create_client(supabase_url, anon_key)
supabase_mhs.postgrest.auth(mhs_token)

print("\n--- ATTEMPTING INSERT AS MAHASISWA ---")
try:
    res = supabase_mhs.table("pengumpulan_tugas").insert({
        "mahasiswa_id": mhs_id,
        "mata_kuliah_id": matkul_id,
        "status_submit": "draft",
        "ai_status": "idle"
    }).execute()
    print("Insert succeeded! Result data:", res.data)
    if res.data:
        sub_id = res.data[0]['id']
        supabase_admin.table("pengumpulan_tugas").delete().eq("id", sub_id).execute()
        print("Cleaned up mahasiswa insert row.")
except Exception as e:
    print("Insert failed as mahasiswa!")
    print("Error class:", e.__class__.__name__)
    print("Error string:", str(e))
    # If the error object has JSON attributes or API error info
    for attr in dir(e):
        if not attr.startswith('_'):
            try:
                val = getattr(e, attr)
                if not callable(val):
                    print(f"  {attr}: {val}")
            except Exception:
                pass

print("\n--- ATTEMPTING INSERT AS SERVICE ROLE ---")
try:
    res = supabase_admin.table("pengumpulan_tugas").insert({
        "mahasiswa_id": mhs_id,
        "mata_kuliah_id": matkul_id,
        "status_submit": "draft",
        "ai_status": "idle"
    }).execute()
    print("Insert succeeded as service role! Result data:", res.data)
    # Clean up the row if it succeeded
    if res.data:
        sub_id = res.data[0]['id']
        supabase_admin.table("pengumpulan_tugas").delete().eq("id", sub_id).execute()
        print("Cleaned up service role insert row.")
except Exception as e:
    print("Insert failed as service role!")
    print("Error string:", str(e))
