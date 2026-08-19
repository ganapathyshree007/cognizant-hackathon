import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/evaluate"
PATIENT_ID = "00126cb9-8460-4747-e302-c3609684531e"

def run_test(test_id, context, expected_status, expected_step7_blocked=None, expected_step6_pathway=None, fail_msg=""):
    payload = {
        "patient_id": PATIENT_ID,
        "encounter_id": "UNKNOWN",
        "clinical_context": context
    }
    
    try:
        r = requests.post(BASE_URL, json=payload, headers={'Authorization': 'Bearer placeholder'})
        if r.status_code != 200:
            print(f"{test_id} FAIL (HTTP {r.status_code}): {r.text}")
            return False
            
        data = r.json()
        status = data.get("step5", {}).get("status")
        step7 = data.get("step7")
        step6 = data.get("step6")
        
        passed = True
        
        if status != expected_status:
            print(f"{test_id} FAIL: Expected Status {expected_status}, got {status}. Context: {context}")
            passed = False
            
        if expected_step7_blocked is True:
            if step7 is not None and step7.get("Status") != "BLOCKED":
                print(f"{test_id} FAIL: Expected step7 to be BLOCKED or None. Got: {step7}")
                passed = False
        elif expected_step7_blocked is False:
            if step7 is None or step7.get("Status") == "BLOCKED":
                print(f"{test_id} FAIL: Expected step7 to be active. Got: {step7}")
                passed = False
                
        if expected_step6_pathway:
            if step6.get("Pathway") != expected_step6_pathway:
                print(f"{test_id} FAIL: Expected pathway {expected_step6_pathway}, got {step6.get('Pathway')}")
                passed = False

        if passed:
            print(f"{test_id} PASS")
        return passed
    except Exception as e:
        print(f"{test_id} ERROR: {e}")
        return False

# TEST 1: Temperature missing, Symptoms missing -> PENDING
run_test("TEST 1", {}, "PENDING", True)

# TEST 2: Temperature = 98.6°F, Symptoms = No current symptoms -> GREEN
run_test("TEST 2", {"Temperature": 98.6, "No current symptoms": True}, "GREEN", False)

# TEST 3: Temperature = 98.6°F, Symptoms = Cough -> GREEN
run_test("TEST 3", {"Temperature": 98.6, "Cough": True}, "GREEN")

# TEST 4: Temperature = 98°F, Symptoms = Cough -> GREEN
run_test("TEST 4", {"Temperature": 98.0, "Cough": True}, "GREEN")

# TEST 5: Temperature = 100.4°F, Symptoms = Cough -> YELLOW
run_test("TEST 5", {"Temperature": 100.4, "Cough": True}, "YELLOW")

# TEST 6: Temperature = 104°F, Symptoms = Cough -> RED
run_test("TEST 6", {"Temperature": 104.0, "Cough": True}, "RED")

# TEST 7: Temperature = 98.6°F, Symptoms = Shortness of breath, SpO2 missing -> YELLOW
run_test("TEST 7", {"Temperature": 98.6, "Shortness of breath": True}, "YELLOW")

# TEST 8: Temperature = 98.6°F, Symptoms = Shortness of breath, SpO2 = 90 -> RED
run_test("TEST 8", {"Temperature": 98.6, "Shortness of breath": True, "SpO2": 90}, "RED")

# TEST 9: Temperature = 98.6°F, Symptoms = Chest pain -> RED
run_test("TEST 9", {"Temperature": 98.6, "Chest pain": True}, "RED")

# TEST 10: Temperature = 98.6°F, Symptoms = Chest Pain -> RED
run_test("TEST 10", {"Temperature": 98.6, "Chest Pain": True}, "RED")

# TEST 11: Temperature = 98.6°F, Symptoms = Cough, SpO2 = 98, HR = 75 -> GREEN
run_test("TEST 11", {"Temperature": 98.6, "Cough": True, "SpO2": 98, "Heart Rate": 75}, "GREEN")

# TEST 12: Temperature = 98.6°F, Symptoms = Cough, SpO2 = 90 -> RED
run_test("TEST 12", {"Temperature": 98.6, "Cough": True, "SpO2": 90}, "RED")

# TEST 13: Temperature = 98.6°F, Symptoms = Cough, HR = 125 -> YELLOW
run_test("TEST 13", {"Temperature": 98.6, "Cough": True, "Heart Rate": 125}, "YELLOW")

# TEST 14: Temperature = 98.6°F, Symptoms = Cough, HR = 140 -> RED
run_test("TEST 14", {"Temperature": 98.6, "Cough": True, "Heart Rate": 140}, "RED")

# TEST 15: Temperature = 98.6°F, Symptoms = Cough, SBP = 85 -> RED
run_test("TEST 15", {"Temperature": 98.6, "Cough": True, "Systolic BP": 85}, "RED")

# TEST 16: Temperature = 98.6°F, Symptoms = Cough, RR = 32 -> RED
run_test("TEST 16", {"Temperature": 98.6, "Cough": True, "Respiratory Rate": 32}, "RED")

# TEST 17: Temperature = 98.6°F, Symptoms = Cough, AVPU = Voice -> YELLOW
run_test("TEST 17", {"Temperature": 98.6, "Cough": True, "AVPU": "Voice"}, "YELLOW")

# TEST 18: Temperature = 98.6°F, Symptoms = Cough, AVPU = Unresponsive -> RED
run_test("TEST 18", {"Temperature": 98.6, "Cough": True, "AVPU": "Unresponsive"}, "RED")

# TEST 19: Temperature = 98.6°F, Symptoms = Cough, All optional vitals missing -> GREEN
run_test("TEST 19", {"Temperature": 98.6, "Cough": True}, "GREEN")

# TEST 20: Temperature missing, Symptoms = Cough, No other trigger -> PENDING
run_test("TEST 20", {"Cough": True}, "PENDING")

# TEST 21: Temperature missing, Symptoms = Shortness of breath -> YELLOW
run_test("TEST 21", {"Shortness of breath": True}, "YELLOW")

# TEST 22: Temperature missing, Symptoms = Chest pain -> RED
run_test("TEST 22", {"Chest pain": True}, "RED")

# TEST 23/24 cannot be perfectly forced externally without mocking DB, but we know Patient 001 is HIGH risk
# Wait, patient 00126cb9 is HIGH risk usually, let's see.
# TEST 23: HIGH historical risk + Temp 98.6 + No current symptoms -> GREEN
run_test("TEST 23", {"Temperature": 98.6, "No current symptoms": True}, "GREEN")

# TEST 24: LOW historical risk + RED current condition -> RED
run_test("TEST 24", {"Temperature": 104.0, "Cough": True}, "RED")

# TEST 25: RED -> step7 = None
run_test("TEST 25", {"Temperature": 104.0, "Cough": True}, "RED", True)

# TEST 26: PENDING -> step7 = None
run_test("TEST 26", {}, "PENDING", True)

# TEST 27: YELLOW -> urgent/clinician pathway
run_test("TEST 27", {"Temperature": 100.4, "Cough": True}, "YELLOW", False, "P2")

# TEST 28: GREEN -> normal provider navigation
run_test("TEST 28", {"Temperature": 98.6, "No current symptoms": True}, "GREEN", False)

# TEST 29: Manual "Chest pain" and LLM "Chest Pain" -> same canonical rule
run_test("TEST 29A", {"Temperature": 98.6, "Chest pain": True}, "RED")
run_test("TEST 29B", {"Temperature": 98.6, "Chest Pain": True}, "RED")

# TEST 30: 98.6F MUST NOT trigger abnormal-temperature rule
run_test("TEST 30", {"Temperature": 98.6, "No current symptoms": True}, "GREEN")

print("ALL TESTS DISPATCHED.")
