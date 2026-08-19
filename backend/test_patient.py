import requests

BASE = "http://localhost:8000"
VALID_ID = "00126cb9-8460-4747-e302-c3609684531e"
INVALID_ID = "definitely-invalid-patient-id"

print("=== TEST 1: VALID PATIENT LOGIN ===")
r1 = requests.post(f"{BASE}/api/patient/login", json={"patient_id": VALID_ID})
print("Status:", r1.status_code)
print("Response:", r1.text)

print("\n=== TEST 2: INVALID PATIENT LOGIN ===")
r2 = requests.post(f"{BASE}/api/patient/login", json={"patient_id": INVALID_ID})
print("Status:", r2.status_code)
print("Response:", r2.text)

print("\n=== TEST 3: VALID PATIENT APPOINTMENTS ===")
token = r1.json().get("token")
r3 = requests.get(f"{BASE}/api/patient/appointments", headers={"Authorization": f"Bearer {token}"})
print("Status:", r3.status_code)
print("Response:", r3.text)

print("\n=== TEST 4: PATIENT PROFILE (VALID) ===")
r4 = requests.get(f"{BASE}/api/patient/profile", headers={"Authorization": f"Bearer {token}"})
print("Status:", r4.status_code)
print("Response:", r4.text)
