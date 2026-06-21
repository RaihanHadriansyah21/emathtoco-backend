import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
backend_env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(backend_env_path)

supabase_url = os.environ.get("SUPABASE_URL")
service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
anon_key = os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhreHhoYWN0cHdpcWR6ZWNyYnh3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE2ODUwNTEsImV4cCI6MjA5NzI2MTA1MX0.5VjFJiFzK0aj-zwQFi_1QmPKrrrX7_P6eFB56ADJlGc")

print("==================================================================")
print("EMATHTOCO — MIGRATION VERIFICATION & PROOF SUITE")
print("==================================================================")

supabase_admin: Client = create_client(supabase_url, service_key)

# Test users
users = {
    "student_a": {
        "email": "mhs12@gmail.com",
        "id": "d6db9404-32a6-4fd6-8ccf-a7cdcac47641"
    },
    "student_b": {
        "email": "mhs1@gmail.com",
        "id": "268486b9-e9b7-4233-acdf-c8279d10b3bc"
    },
    "lecturer_a": {
        "email": "pakgelarbudiman@emathtoco.com",
        "id": "aa36f617-857c-400a-ae85-444b4284e2da"
    },
    "lecturer_b": {
        "email": "mhs2@gmail.com", # Using mhs2 as Lecturer B
        "id": "cd97c16f-286a-4bfa-a9a9-fb09dfd837d1"
    },
    "admin": {
        "email": "emathtoco@gmail.com",
        "id": "eb34d26b-76d9-4b9f-b43a-7f635bf2fc00"
    }
}

# 1. Reset passwords to password123
print("\n=== STEP 1: RESETTING PASSWORDS TO password123 ===")
for name, uinfo in users.items():
    uid = uinfo["id"]
    email = uinfo["email"]
    try:
        try:
            supabase_admin.auth.admin.update_user_by_id(uid, {"password": "password123"})
        except Exception:
            supabase_admin.auth.admin.update_user_by_id(user_id=uid, attributes={"password": "password123"})
        print(f"[OK] Password reset for {name} ({email})")
    except Exception as e:
        print(f"[ERROR] Failed to reset password for {name}: {e}")

# 2. Promote Lecturer B to Dosen role if not already
print("\n=== STEP 2: PROMOTING LECTURER B AND CREATING TEST COURSE/SUBMISSIONS ===")
try:
    # Update profile role
    supabase_admin.table("profil_pengguna").update({"role": "Dosen", "nama_lengkap": "Lecturer B Test"}).eq("id", users["lecturer_b"]["id"]).execute()
    print("[OK] Lecturer B promoted to Dosen role in public.profil_pengguna.")

    # Create Course B if not exists
    supabase_admin.table("mata_kuliah").upsert({
        "id": "c3d47192-85c6-4fb7-b9ca-edaa13a9954e",
        "nama_matkul": "Mata Kuliah B Test",
        "nama_dosen": "Lecturer B Test",
        "icon_name": "math",
        "kode_matkul": "MK-B"
    }).execute()
    print("[OK] Course B upserted.")

    # Assign Lecturer B to Course B
    supabase_admin.table("dosen_mata_kuliah").upsert({
        "id": "1868e354-87e6-47df-ac4d-ce79804ee831",
        "dosen_id": users["lecturer_b"]["id"],
        "mata_kuliah_id": "c3d47192-85c6-4fb7-b9ca-edaa13a9954e"
    }).execute()
    print("[OK] Lecturer B assigned to Course B.")

    # Create Submission A for Student A (Course A)
    sub_a_id = "d6db9404-32a6-4fd6-8ccf-a7cdcac4760a"
    supabase_admin.table("pengumpulan_tugas").upsert({
        "id": sub_a_id,
        "mahasiswa_id": users["student_a"]["id"],
        "mata_kuliah_id": "c3d47192-85c6-4fb7-b9ca-edaa13a9954f",
        "status_submit": "draft",
        "ai_status": "idle",
        "nilai_akhir": 0
    }).execute()
    print("[OK] Submission A created.")

    # Create Submission B for Student B (Course B)
    sub_b_id = "268486b9-e9b7-4233-acdf-c8279d10b30b"
    supabase_admin.table("pengumpulan_tugas").upsert({
        "id": sub_b_id,
        "mahasiswa_id": users["student_b"]["id"],
        "mata_kuliah_id": "c3d47192-85c6-4fb7-b9ca-edaa13a9954e",
        "status_submit": "draft",
        "ai_status": "idle",
        "nilai_akhir": 0
    }).execute()
    print("[OK] Submission B created.")

except Exception as e:
    print(f"[ERROR] Data setup failed: {e}")

# 3. Create clients and authenticate
print("\n=== STEP 3: GETTING ACCESS TOKENS / DIRECT SIGN-IN ===")
client_a = create_client(supabase_url, anon_key)
client_b = create_client(supabase_url, anon_key)
client_lect_a = create_client(supabase_url, anon_key)
client_lect_b = create_client(supabase_url, anon_key)
client_admin = create_client(supabase_url, anon_key)

clients = {
    "student_a": client_a,
    "student_b": client_b,
    "lecturer_a": client_lect_a,
    "lecturer_b": client_lect_b,
    "admin": client_admin
}

for name, client in clients.items():
    try:
        client.auth.sign_in_with_password({"email": users[name]["email"], "password": "password123"})
        print(f"[OK] Client signed in for {name}")
    except Exception as e:
        print(f"[ERROR] Auth failed for {name}: {e}")

# 4. Upload test files for Student A and Student B
print("\n=== STEP 4: UPLOADING DUMMY STORAGE FILES ===")
file_a_path = f"{users['student_a']['id']}/{sub_a_id}/S-1A.jpg"
file_b_path = f"{users['student_b']['id']}/{sub_b_id}/S-1A.jpg"
dummy_data = b"DUMMY_IMAGE_BYTES"

# Upload File A using Student A client
try:
    try:
        client_a.storage.from_("lembar-jawaban").remove([file_a_path])
    except Exception:
        pass
    client_a.storage.from_("lembar-jawaban").upload(file_a_path, dummy_data, file_options={"content-type": "image/jpeg"})
    print(f"[OK] Student A uploaded file A: {file_a_path}")
except Exception as e:
    print(f"[ERROR] Student A upload file A failed: {e}")

# Upload File B using Student B client
try:
    try:
        client_b.storage.from_("lembar-jawaban").remove([file_b_path])
    except Exception:
        pass
    client_b.storage.from_("lembar-jawaban").upload(file_b_path, dummy_data, file_options={"content-type": "image/jpeg"})
    print(f"[OK] Student B uploaded file B: {file_b_path}")
except Exception as e:
    print(f"[ERROR] Student B upload file B failed: {e}")


def run_proof_cases(stage: str):
    print(f"\n=== PROOF CASES ({stage}) ===")
    
    # CASE A: Student A reads own file.
    try:
        data = client_a.storage.from_("lembar-jawaban").download(file_a_path)
        print(f"CASE A (Student A reads own file): ALLOWED (Data: {len(data)} bytes) -> PASS")
    except Exception as e:
        print(f"CASE A (Student A reads own file): BLOCKED ({e}) -> FAIL")
        
    # CASE B: Student B reads Student A file.
    try:
        data = client_b.storage.from_("lembar-jawaban").download(file_a_path)
        print(f"CASE B (Student B reads Student A file): ALLOWED (Data: {len(data)} bytes) -> FAIL")
    except Exception as e:
        print(f"CASE B (Student B reads Student A file): BLOCKED ({e}) -> PASS")
        
    # CASE C: Student B creates signed URL for Student A file.
    try:
        res = client_b.storage.from_("lembar-jawaban").create_signed_url(file_a_path, 3600)
        # Check if the returned url works or is created
        if res and isinstance(res, dict) and "signedUrl" in res:
            print(f"CASE C (Student B signs Student A file): ALLOWED ({res['signedUrl'][:60]}...) -> FAIL")
        elif isinstance(res, str):
            print(f"CASE C (Student B signs Student A file): ALLOWED ({res[:60]}...) -> FAIL")
        else:
            print(f"CASE C (Student B signs Student A file): ALLOWED ({res}) -> FAIL")
    except Exception as e:
        print(f"CASE C (Student B signs Student A file): BLOCKED ({e}) -> PASS")
        
    # CASE D: Lecturer A reads Lecturer B submission.
    try:
        data = client_lect_a.storage.from_("lembar-jawaban").download(file_b_path)
        print(f"CASE D (Lecturer A reads Lecturer B file): ALLOWED (Data: {len(data)} bytes) -> FAIL")
    except Exception as e:
        print(f"CASE D (Lecturer A reads Lecturer B file): BLOCKED ({e}) -> PASS")
        
    # CASE E: Admin reads all files.
    try:
        data = client_admin.storage.from_("lembar-jawaban").download(file_a_path)
        data2 = client_admin.storage.from_("lembar-jawaban").download(file_b_path)
        print(f"CASE E (Admin reads all files): ALLOWED (A: {len(data)}, B: {len(data2)} bytes) -> PASS")
    except Exception as e:
        print(f"CASE E (Admin reads all files): BLOCKED ({e}) -> FAIL")

    # CASE F: Lecturer B reads own course submission (Student B file).
    try:
        data = client_lect_b.storage.from_("lembar-jawaban").download(file_b_path)
        print(f"CASE F (Lecturer B reads own course file): ALLOWED (Data: {len(data)} bytes) -> PASS")
    except Exception as e:
        print(f"CASE F (Lecturer B reads own course file): BLOCKED ({e}) -> FAIL")

# Run AFTER stage
run_proof_cases("AFTER HARDENING")

print("\n==================================================================")
print("PROOF CASES COMPLETED")
print("==================================================================")
