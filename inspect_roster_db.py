import sys
from utils.supabase_client import supabase

print("--- FETCH MATA KULIAH ---")
res_mk = supabase.table("mata_kuliah").select("id, nama_matkul, kode_matkul").execute()
for r in res_mk.data:
    print(f"Course: {r['nama_matkul']} | Code: {r['kode_matkul']} | ID: {r['id']}")

print("\n--- FETCH ENROLLMENTS ---")
res_enroll = supabase.table("mahasiswa_mata_kuliah").select("*").execute()
print(f"Total enrollment rows: {len(res_enroll.data)}")
for r in res_enroll.data[:15]:
    print(r)

print("\n--- FETCH STUDENT PROFILES ---")
res_profiles = supabase.table("profil_pengguna").select("id, nama_lengkap, role, nim_nip").eq("role", "mahasiswa").execute()
print(f"Total student profiles: {len(res_profiles.data)}")
for p in res_profiles.data[:15]:
    print(p)
