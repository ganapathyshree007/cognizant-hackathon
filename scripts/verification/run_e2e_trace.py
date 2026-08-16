import os
import sys
import unittest.mock
import json

os.environ['NAVIGATOR_PROJECT_ROOT'] = r'd:\cognizant-hackathon-main'

# Mock joblib to not actually load a real model if it's missing, but wait, the model DOES exist because tests pass.
# Let's NOT mock joblib so we use the real XGBoost model!
# Wait, in the tests we mocked joblib. Does the real model exist?
import pathlib
if not (pathlib.Path(r'd:\cognizant-hackathon-main') / 'model_artifacts' / 'repeat_ed_risk_model.joblib').exists():
    sys.modules['joblib'] = unittest.mock.MagicMock()
    original_read_text = pathlib.Path.read_text
    def mock_read_text(self, *args, **kwargs):
        if 'model_report.json' in str(self):
            return json.dumps({"feature_columns": ["ed_visits_90d", "outpatient_visits_90d", "inpatient_visits_90d", "age"], "selected_operating_threshold": 0.5})
        return original_read_text(self, *args, **kwargs)
    pathlib.Path.read_text = mock_read_text

import pandas as pd
def mock_read_csv(*args, **kwargs):
    # Fake dataframe for outcomes
    return pd.DataFrame({
        'member_id': ['e2e_member'],
        'start_date': [pd.Timestamp('2023-05-01')],
        'ed_candidate_flag': [1],
        'encounter_type': ['OUTPATIENT']
    })
pd.read_csv = mock_read_csv

sys.path.insert(0, r'd:\cognizant-hackathon-main')
import backend.main
from fastapi.testclient import TestClient

def mock_kg_case(case_id):
    # Return exactly what the user specified
    return {
        'ed_visits_90d': 4,
        'outpatient_visits_90d': 0,
        'inpatient_visits_90d': 1,
        'age': 67,
        'index_date': '2023-01-01'
    }, ["Patient has a history of high ED utilization.", "No recent outpatient engagement."]

# We must patch kg_case so it doesn't fail looking for a real graph DB for 'e2e_case'
backend.main.kg_case = mock_kg_case

# Mock the predict_proba to return a high risk score if we're using the mocked joblib
if getattr(backend.main.MODEL, 'predict_proba', None) is None or isinstance(backend.main.MODEL, unittest.mock.MagicMock):
    backend.main.MODEL.predict_proba = lambda x: [[0.1, 0.85]]

app = backend.main.app
client = TestClient(app)
headers = {"x-api-key": "change-me"}

def run_trace():
    print("="*60)
    print("UC07 END-TO-END TRACE")
    print("="*60)
    
    member_id = "e2e_member"
    case_id = "e2e_case"
    
    # 1. XGBoost Scoring
    print("\n[1] SCORE: XGBoost Risk Model")
    score_payload = {
        "features": {
            "ed_visits_90d": 4,
            "outpatient_visits_90d": 0,
            "inpatient_visits_90d": 1,
            "age": 67
        }
    }
    res_score = client.post('/v1/score', headers=headers, json=score_payload)
    print(json.dumps(res_score.json(), indent=2))
    
    # 2. Safety Gate
    print("\n[2] SAFETY GATE")
    safety_payload = {
        "case_id": case_id,
        "patient_id": member_id,
        "new_context": {
            "triage_notes": "Patient reports mild discomfort, no acute distress.",
            "vitals": "Stable, normal range",
            "clinician_assessment": "Non-emergent, suitable for outpatient follow-up"
        }
    }
    res_safety = client.post('/v1/safety/assess', headers=headers, json=safety_payload)
    print(json.dumps(res_safety.json(), indent=2))
    safety_session_id = res_safety.json()['session_id']
    
    # 3. Navigation Opportunity
    print("\n[3] NAVIGATION OPPORTUNITY")
    opp_payload = {
        "case_id": case_id,
        "safety_session_id": safety_session_id
    }
    res_opp = client.post('/v1/navigation-opportunity', headers=headers, json=opp_payload)
    print(json.dumps(res_opp.json(), indent=2))
    opp_session_id = res_opp.json()['opportunity_id']
    
    # 4. Driver Analysis
    print("\n[4] DRIVER ANALYSIS")
    driver_payload = {
        "case_id": case_id,
        "opportunity_session_id": opp_session_id
    }
    res_driver = client.post('/v1/navigation-drivers', headers=headers, json=driver_payload)
    print(json.dumps(res_driver.json(), indent=2))
    driver_session_id = res_driver.json()['driver_session_id']
    
    # 5. Pathway Recommendation
    print("\n[5] PATHWAY RECOMMENDATION")
    pathway_payload = {
        "case_id": case_id,
        "reviewer_id": "system",
        "driver_session_id": driver_session_id,
        "reviewer_cleared": True
    }
    res_pathway = client.post('/v1/pathways', headers=headers, json=pathway_payload)
    print(json.dumps(res_pathway.json(), indent=2))
    pathway_session_id = res_pathway.json()['pathway_session_id']
    
    # 6. Provider Recommendation
    print("\n[6] PROVIDER RECOMMENDATION")
    provider_payload = {
        "pathway_session_id": pathway_session_id,
        "require_telehealth": False,
        "limit": 3
    }
    res_provider = client.post('/v1/providers/recommend', headers=headers, json=provider_payload)
    print(json.dumps(res_provider.json(), indent=2))
    provider_session_id = res_provider.json()['provider_session_id']
    
    # 7. Care Manager Review
    print("\n[7] CARE MANAGER REVIEW")
    review_payload = {
        "provider_session_id": provider_session_id,
        "reviewer_id": "human_cm_1",
        "decision": "APPROVE"
    }
    res_review = client.post('/v1/care-manager/review', headers=headers, json=review_payload)
    print(json.dumps(res_review.json(), indent=2))
    review_id = res_review.json()['review_id']
    
    # 8. Intervention
    print("\n[8] INTERVENTION")
    int_payload = {
        "review_id": review_id
    }
    res_int = client.post('/v1/interventions', headers=headers, json=int_payload)
    print(json.dumps(res_int.json(), indent=2))
    intervention_id = res_int.json()['intervention_id']
    
    # 9. Outcome
    print("\n[9] OUTCOME")
    out_payload = {
        "window_days": 90
    }
    res_out = client.post(f'/v1/interventions/{intervention_id}/outcomes', headers=headers, json=out_payload)
    print(json.dumps(res_out.json(), indent=2))
    
    # 10. Member History Verification
    print("\n[10] MEMBER HISTORY (SQLite Verif)")
    import sqlite3
    with sqlite3.connect(backend.main.DB) as c:
        rows = c.execute("SELECT event_type, event_date, source, details FROM member_history WHERE member_id=?", (case_id,)).fetchall()
        for r in rows:
            print(f"EVENT: {r[0]} | DATE: {r[1]} | SOURCE: {r[2]} | DETAILS: {r[3]}")

if __name__ == '__main__':
    run_trace()
