import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase_admin: Client = create_client(supabase_url, service_key)

def run_query(sql):
    # Using POST to supabase RPC or similar if available, but since we have service role client
    # we can run a custom postgres query by executing it through RPC if there's any.
    # Wait, does the project have a custom RPC like 'execute_sql'? Let's check!
    try:
        res = supabase_admin.rpc("execute_sql", {"query": sql}).execute()
        return res.data
    except Exception as e:
        return f"Error executing RPC: {e}"

# Let's try if RPC execute_sql works. If not, we can query views or try another way.
print("Testing execute_sql RPC...")
test = run_query("SELECT 1 as val;")
print("Result:", test)

# Let's query column details for lembar_jawaban and hasil_prediksi
tables = ["pengumpulan_tugas", "lembar_jawaban", "hasil_prediksi"]
for table in tables:
    print(f"\n==================================================")
    print(f"SCHEMA FOR {table}")
    print(f"==================================================")
    cols = run_query(f"SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_name = '{table}';")
    print(json.dumps(cols, indent=2))
    
    print(f"\nCONSTRAINTS FOR {table}")
    print(f"==================================================")
    cons = run_query(f"SELECT conname, pg_get_constraintdef(c.oid) FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace WHERE conrelid = '{table}'::regclass;")
    print(json.dumps(cons, indent=2))

print(f"\n==================================================")
print("RLS POLICIES")
print(f"==================================================")
pols = run_query("SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check FROM pg_policies WHERE tablename IN ('pengumpulan_tugas', 'lembar_jawaban', 'hasil_prediksi');")
print(json.dumps(pols, indent=2))
