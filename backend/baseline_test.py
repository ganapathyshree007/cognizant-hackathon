import os
import requests
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://rjciwhclrmwpobinvbqd.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_6UHYXssCv-G45CFuXWSGig_c10iZSMq")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    print("1. Authenticating as Care Manager...")
    session = supabase.auth.sign_in_with_password({"email": "cm@test.com", "password": "password123"})
    cm_token = session.session.access_token
    print("PASS: Authentication Successful")
except Exception as e:
    print("FAIL: Authentication failed", e)
    exit(1)

headers = {"Authorization": f"Bearer {cm_token}"}

print("\n2. Testing Patient Search...")
resp = requests.get("http://localhost:8000/api/patients/search?query=00126", headers=headers)
if resp.status_code == 200:
    data = resp.json()
    print(f"PASS: Patient search returned {len(data)} results.")
    patient_id = data[0]['PATIENT_ID'] if data else "00126cb9-8460-4747-e302-c3609684531e"
    encounter_id = data[0]['ENCOUNTER_ID'] if data else "1234"
else:
    print("FAIL: Patient Search", resp.text)
    patient_id = "00126cb9-8460-4747-e302-c3609684531e"
    encounter_id = "1234"

print("\n3. Testing Evaluate (ML + Safety + Matching)...")
eval_req = {
    "patient_id": patient_id,
    "encounter_id": encounter_id,
    "clinical_context": {"Temperature": 99, "Pain": 2, "required_specialty_hint": "Cardiology"}
}
resp = requests.post("http://localhost:8000/api/evaluate", json=eval_req, headers=headers)
if resp.status_code == 200:
    data = resp.json()
    print("PASS: Evaluate successful.")
    print("  Risk Score:", data.get('step4', {}).get('score'))
    print("  Risk Band:", data.get('step4', {}).get('band'))
    print("  Safety Gate:", data.get('step5', {}).get('status'))
    print("  Pathway:", data.get('step6', {}).get('Pathway'))
    
    prov_opts = data.get('step7', {}).get('Options', [])
    print(f"  Matched Providers: {len(prov_opts)}")
    if prov_opts:
        print(f"  Top Provider: {prov_opts[0].get('Name')}")
else:
    print("FAIL: Evaluate", resp.text)

print("\n4. Testing Dashboard Stats...")
resp = requests.get("http://localhost:8000/api/dashboard/stats", headers=headers)
if resp.status_code == 200:
    print("PASS: Dashboard stats:", resp.json())
else:
    print("FAIL: Dashboard stats", resp.text)

print("\n5. Testing LLM Extraction...")
llm_req = {"symptoms": "I have a fever and my chest hurts a lot."}
resp = requests.post("http://localhost:8000/api/symptoms/llm-extract", json=llm_req, headers=headers)
if resp.status_code == 200:
    print("PASS: LLM Extraction:", resp.json())
else:
    print("FAIL: LLM Extraction", resp.text)

print("\nDONE.")
