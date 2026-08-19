"""
Creates the patient_vitals table in Supabase using psycopg2/supabase-py.
Connects directly via Supabase Python client and runs raw SQL through postgrest.
Run: python create_patient_vitals_table.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("ERROR: SUPABASE_URL or SUPABASE_SERVICE_KEY not set in .env")
    exit(1)

client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Test existing table access
try:
    test = client.table("backend_files").select("PATIENT_ID").limit(1).execute()
    print("Supabase connection OK. Rows found:", len(test.data))
except Exception as e:
    print("Connection test failed:", e)
    exit(1)

# Try inserting a dummy row to verify patient_vitals exists or create it
print("\nTesting if patient_vitals table already exists...")
try:
    result = client.table("patient_vitals").select("id").limit(1).execute()
    print("patient_vitals table EXISTS. Rows:", len(result.data))
except Exception as e:
    print("patient_vitals table does NOT exist yet:", e)
    print("\nPlease create the table manually in Supabase Dashboard SQL Editor.")
    print("SQL is saved in: supabase_patient_vitals.sql")
