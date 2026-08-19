import requests
import json

BASE_URL = "http://localhost:8000/api/evaluate"
PATIENT_ID = "00126cb9-8460-4747-e302-c3609684531e"

def eval_state(name, context):
    payload = {
        "patient_id": PATIENT_ID,
        "encounter_id": "UNKNOWN",
        "clinical_context": context
    }
    r = requests.post(BASE_URL, json=payload, headers={'Authorization': 'Bearer foo'})
    data = r.json()
    status = data.get("step5", {}).get("status")
    step7 = data.get("step7", {})
    return status, step7

print("=== GREEN ===")
s, s7 = eval_state("GREEN", {"Temperature": 98.6, "No current symptoms": True})
print(f"Status: {s}")
print(f"step7: {json.dumps(s7)}")

print("\n=== YELLOW ===")
s, s7 = eval_state("YELLOW", {"Temperature": 100.4, "Cough": True})
print(f"Status: {s}")
print(f"step7: {json.dumps(s7)}")

print("\n=== RED ===")
s, s7 = eval_state("RED", {"Temperature": 104.0, "Cough": True})
print(f"Status: {s}")
print(f"step7: {json.dumps(s7)}")

print("\n=== PENDING ===")
s, s7 = eval_state("PENDING", {})
print(f"Status: {s}")
print(f"step7: {json.dumps(s7)}")
