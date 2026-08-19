import os
import time
import requests
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://rjciwhclrmwpobinvbqd.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
API_URL = "http://localhost:8000"

print("Initializing E2E Test...")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# We need a valid care manager ID for the DB. We can mock a JWT token 
# or use the service role key to insert records directly, but to test the API,
# we need a real JWT token. Since creating real users and getting JWTs requires
# passwords and the public API, we can use the Supabase Auth API.

import uuid
cm_email = f"cm_test_{uuid.uuid4().hex[:6]}@test.com"
cm_password = "password123"

patient_email = f"pat_test_{uuid.uuid4().hex[:6]}@test.com"
patient_password = "password123"

print(f"1. Creating Care Manager: {cm_email}")
cm_auth_resp = supabase.auth.admin.create_user({
    "email": cm_email,
    "password": cm_password,
    "email_confirm": True,
    "user_metadata": {"full_name": "Test CM", "role": "CARE_MANAGER"}
})
cm_id = cm_auth_resp.user.id

# We need a token to call the API.
cm_sign_in = supabase.auth.sign_in_with_password({"email": cm_email, "password": cm_password})
cm_token = cm_sign_in.session.access_token

headers = {"Authorization": f"Bearer {cm_token}", "Content-Type": "application/json"}

print("2. Testing Patient Search...")
search_resp = requests.get(f"{API_URL}/api/patients/search?query=1", headers=headers)
assert search_resp.status_code == 200, search_resp.text
results = search_resp.json()
print(f"   Found {len(results)} patients.")
if len(results) == 0:
    print("   ERROR: No patients found in DB.")
    exit(1)

test_patient_id = results[0]['PATIENT_ID']
test_encounter_id = results[0]['ENCOUNTER_ID']
print(f"   Selected Patient: {test_patient_id}, Encounter: {test_encounter_id}")

print("2.5 Simulating Admin Demo Patient Linking...")
pat_sign_in = supabase.auth.admin.create_user({
    "email": patient_email,
    "password": patient_password,
    "email_confirm": True,
    "user_metadata": {"full_name": "Test Patient", "role": "PATIENT"}
})
pat_id = pat_sign_in.user.id

# Link patient in DB (Admin Demo Link simulation)
supabase.table("patients").insert({
    "profile_id": pat_id,
    "patient_id": test_patient_id,
    "name": "Test Patient"
}).execute()

print("3. Testing Step 4 (Historical Risk) & Evaluate API (Stage 1)...")
eval_resp = requests.post(f"{API_URL}/api/evaluate", headers=headers, json={
    "patient_id": test_patient_id,
    "encounter_id": test_encounter_id,
    "clinical_context": {}
})
assert eval_resp.status_code == 200, eval_resp.text
eval_data = eval_resp.json()
print(f"   Step 4 Risk Band: {eval_data['step4']['band']} | Score: {eval_data['step4']['score']}")
assert eval_data['step5']['status'] == "PENDING"

print("4. Testing Evaluate API (Stage 2) with GREEN Vitals...")
green_eval_resp = requests.post(f"{API_URL}/api/evaluate", headers=headers, json={
    "patient_id": test_patient_id,
    "encounter_id": test_encounter_id,
    "clinical_context": {"SpO2": 98, "Heart Rate": 70, "AVPU": "A", "Bleeding": "No"}
})
green_data = green_eval_resp.json()
print(f"   Step 5 Safety Status: {green_data['step5']['status']}")
print(f"   Step 6 Pathway: {green_data['step6']['Pathway']}")
print(f"   Step 7 Provider Matching Status: {green_data['step7']['Status']}")
assert green_data['step5']['status'] == "GREEN"
assert green_data['step7']['Status'] == "SUCCESS"
provider = green_data['step7']['Options'][0]

print("5. Testing Audit Trail API (Approve)...")
audit_resp = requests.post(f"{API_URL}/api/audit", headers=headers, json={
    "patient_id": test_patient_id,
    "encounter_id": test_encounter_id,
    "action": "APPROVE",
    "reason": "Test approval",
    "system_pathway": green_data['step6']['Pathway'],
    "system_provider": provider['Name'],
    "selected_provider": provider['Name']
})
assert audit_resp.status_code == 200, audit_resp.text
print("   Audit recorded successfully.")

print("6. Testing Appointment Creation...")
appt_resp = requests.post(f"{API_URL}/api/appointments", headers=headers, json={
    "patient_id": test_patient_id,
    "encounter_id": test_encounter_id,
    "provider_name": provider['Name'],
    "provider_npi": str(provider.get('NPI', 'N/A')),
    "pac_id": str(provider.get('PAC_ID', 'N/A')),
    "provider_specialty": provider.get('Specialty', 'General'),
    "appointment_date": "2026-09-01",
    "appointment_time": "10:00"
})
assert appt_resp.status_code == 200, appt_resp.text
appt_id = appt_resp.json()['appointment_id']
print(f"   Appointment scheduled successfully: {appt_id}")

print("7. Testing Post-Consultation Workflow...")
print("   Updating status to Completed...")
update_resp = requests.put(f"{API_URL}/api/appointments/{appt_id}", headers=headers, json={"status": "Completed"})
assert update_resp.status_code == 200, update_resp.text

print("   Submitting Outcome...")
outcome_resp = requests.post(f"{API_URL}/api/outcomes", headers=headers, json={
    "appointment_id": appt_id,
    "patient_id": test_patient_id,
    "encounter_id": test_encounter_id,
    "clinical_notes": "Patient condition improved significantly.",
    "follow_up_required": False
})
assert outcome_resp.status_code == 200, outcome_resp.text
print("   Outcome saved successfully.")

print("8. Testing RED Safety Gate Override...")
red_eval_resp = requests.post(f"{API_URL}/api/evaluate", headers=headers, json={
    "patient_id": test_patient_id,
    "encounter_id": test_encounter_id,
    "clinical_context": {"SpO2": 85, "Heart Rate": 130, "AVPU": "U", "Bleeding": "Yes"}
})
red_data = red_eval_resp.json()
print(f"   Step 5 Safety Status: {red_data['step5']['status']}")
print(f"   Step 7 Provider Matching Status: {red_data['step7']['Status']}")
assert red_data['step5']['status'] == "RED"
assert red_data['step7']['Status'] == "BLOCKED"
print("   Routine provider matching is successfully blocked.")

print("9. Fetching Appointments (Patient Dashboard Simulation)...")
pat_auth = supabase.auth.sign_in_with_password({"email": patient_email, "password": patient_password})
pat_headers = {"Authorization": f"Bearer {pat_auth.session.access_token}", "Content-Type": "application/json"}

appts_resp = requests.get(f"{API_URL}/api/appointments/{test_patient_id}", headers=pat_headers)
assert appts_resp.status_code == 200, appts_resp.text
print(f"   Patient sees {len(appts_resp.json())} appointments.")

# Clean up
supabase.auth.admin.delete_user(cm_id)
supabase.auth.admin.delete_user(pat_id)

print("\nAll E2E checks passed successfully! The Post-Consultation Loop is fully operational.")
