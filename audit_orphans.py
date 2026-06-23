import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase_admin: Client = create_client(supabase_url, service_key)

def list_files_recursive(bucket, folder=""):
    files = []
    try:
        res = supabase_admin.storage.from_(bucket).list(folder, options={"limit": 100})
        for item in res:
            name = item["name"]
            # Skip placeholder or special files if any
            if name == ".placeholder":
                continue
            is_folder = item.get("id") is None
            item_path = f"{folder}/{name}" if folder else name
            if is_folder:
                files.extend(list_files_recursive(bucket, item_path))
            else:
                files.append({
                    "path": item_path,
                    "size": item.get("metadata", {}).get("size", 0) or item.get("size", 0)
                })
    except Exception as e:
        print(f"Error listing folder '{folder}': {e}")
    return files

def audit_orphans():
    print("--- RUNNING STORAGE ORPHAN FILE AUDIT ---")
    bucket = "lembar-jawaban"
    
    # 1. Fetch all image_urls from database
    try:
        db_res = supabase_admin.table("lembar_jawaban").select("image_url").execute()
        db_paths = {row["image_url"] for row in db_res.data if row.get("image_url")}
        print(f"Total database sheet rows with file paths: {len(db_paths)}")
    except Exception as e:
        print(f"Error fetching database rows: {e}")
        return
        
    # 2. Scan storage bucket recursively
    print("Scanning storage bucket 'lembar-jawaban' recursively...")
    storage_files = list_files_recursive(bucket)
    print(f"Total files in storage bucket: {len(storage_files)}")
    
    # 3. Compare and find orphans
    orphans = []
    total_orphan_size = 0
    
    for f in storage_files:
        path = f["path"]
        size = f["size"]
        if path not in db_paths:
            orphans.append(f)
            total_orphan_size += size
            
    print(f"\n--- AUDIT RESULTS ---")
    print(f"Orphan File Count: {len(orphans)}")
    print(f"Orphan File Size:  {total_orphan_size} bytes ({total_orphan_size / 1024 / 1024:.2f} MB)")
    
    if orphans:
        print("\nORPHAN FILE PATHS:")
        for o in orphans[:50]: # limit output
            print(f"  - Path: {o['path']} | Size: {o['size']} bytes")
        if len(orphans) > 50:
            print(f"  ... and {len(orphans) - 50} more orphans.")
    else:
        print("No orphan files found. Storage hygiene is clean!")

if __name__ == "__main__":
    audit_orphans()
