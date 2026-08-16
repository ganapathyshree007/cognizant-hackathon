import os
os.environ['NAVIGATOR_PROJECT_ROOT'] = r'd:\cognizant-hackathon-main'
os.environ['NAVIGATOR_PROJECT_ROOT'] = r'd:\cognizant-hackathon-main'
import json
import sys
import unittest.mock
import pathlib

sys.modules['joblib'] = unittest.mock.MagicMock()
original_read_text = pathlib.Path.read_text
def mock_read_text(self, *args, **kwargs):
    if 'model_report.json' in str(self):
        return json.dumps({"feature_columns": ["ed_visits_90d", "outpatient_visits_90d", "inpatient_visits_90d", "age"], "selected_operating_threshold": 0.5})
    return original_read_text(self, *args, **kwargs)
pathlib.Path.read_text = mock_read_text

def mock_kg_case(case_id):
    return {
        'ed_visits_90d': 4,
        'outpatient_visits_90d': 0,
        'inpatient_visits_90d': 1,
        'age': 67
    }, ["HIGH_RECENT_ED_UTILIZATION", "LOW_OUTPATIENT_UTILIZATION"]

import backend.main
backend.main.kg_case = mock_kg_case
from fastapi.testclient import TestClient
from backend.main import app

def run_safety_demo():
    client = TestClient(app)
    headers = {'x-api-key': 'change-me'}
    
    print("============================================================")
    print("SAFETY DEMO SCENARIO")
    print("============================================================\n")
    
    # 1. Safety Gate with emergency indicator
    print("[1] SAFETY GATE (Emergency Scenario)")
    safety_payload = {
        "case_id": "demo-case-999",
        "patient_id": "demo-member-999",
        "new_context": {
            "vitals": {"hr": 130, "bp": "80/50"},
            "triage_notes": "Patient reports severe chest pain and shortness of breath.",
            "clinician_assessment": "Possible acute myocardial infarction",
            "_test_fixture_trigger_emergency": True
        }
    }
    res_safety = client.post('/v1/safety/assess', headers=headers, json=safety_payload)
    print(json.dumps(res_safety.json(), indent=2))
    safety_session_id = res_safety.json()['session_id']
    
    # 2. Try Navigation Opportunity
    print("\n[2] NAVIGATION OPPORTUNITY (Attempting after POSSIBLE_EMERGENCY)")
    opp_payload = {
        "case_id": "demo-case-999",
        "safety_session_id": safety_session_id
    }
    res_opp = client.post('/v1/navigation-opportunity', headers=headers, json=opp_payload)
    print(f"Status Code: {res_opp.status_code}")
    print(json.dumps(res_opp.json(), indent=2))

if __name__ == "__main__":
    run_safety_demo()
