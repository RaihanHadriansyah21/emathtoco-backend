import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase_admin: Client = create_client(supabase_url, service_key)

def check_pengumpulan_duplicates():
    print("--- CHECKING PENGUMPULAN_TUGAS DUPLICATES ---")
    res = supabase_admin.table("pengumpulan_tugas").select("id, mahasiswa_id, mata_kuliah_id, status_submit, created_at").execute()
    data = res.data
    
    seen = {}
    duplicates = []
    
    for row in data:
        key = (row['mahasiswa_id'], row['mata_kuliah_id'])
        if key in seen:
            seen[key].append(row)
            if key not in [d[0] for d in duplicates]:
                duplicates.append((key, seen[key]))
        else:
            seen[key] = [row]
            
    print(f"Total rows in pengumpulan_tugas: {len(data)}")
    print(f"Number of unique student-course pairs: {len(seen)}")
    print(f"Duplicate pairs count: {len(duplicates)}")
    
    if duplicates:
        print("\nDUPLICATE DETAILS:")
        for key, rows in duplicates:
            print(f"Student: {key[0]} | Course: {key[1]}")
            for r in rows:
                print(f"  - Row ID: {r['id']} | Status: {r['status_submit']} | Created: {r['created_at']}")
    return duplicates

def check_lembar_duplicates():
    print("\n--- CHECKING LEMBAR_JAWABAN DUPLICATES ---")
    res = supabase_admin.table("lembar_jawaban").select("id, pengumpulan_tugas_id, section_code, image_url, status, created_at").execute()
    data = res.data
    
    seen = {}
    duplicates = []
    
    for row in data:
        key = (row['pengumpulan_tugas_id'], row['section_code'])
        if key in seen:
            seen[key].append(row)
            if key not in [d[0] for d in duplicates]:
                duplicates.append((key, seen[key]))
        else:
            seen[key] = [row]
            
    print(f"Total rows in lembar_jawaban: {len(data)}")
    print(f"Number of unique submission-slot pairs: {len(seen)}")
    print(f"Duplicate pairs count: {len(duplicates)}")
    
    if duplicates:
        print("\nDUPLICATE DETAILS:")
        for key, rows in duplicates:
            print(f"Submission: {key[0]} | Section: {key[1]}")
            for r in rows:
                print(f"  - Row ID: {r['id']} | Status: {r['status']} | Created: {r['created_at']}")
    return duplicates

if __name__ == "__main__":
    check_pengumpulan_duplicates()
    check_lembar_duplicates()
