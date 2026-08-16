import os
import sys
import unittest.mock
import json
import uuid

os.environ['NAVIGATOR_PROJECT_ROOT'] = r'd:\cognizant-hackathon-main'
sys.modules['joblib'] = unittest.mock.MagicMock()

import pathlib
original_read_text = pathlib.Path.read_text
def mock_read_text(self, *args, **kwargs):
    if 'model_report.json' in str(self):
        return json.dumps({"feature_columns": [], "selected_operating_threshold": 0.5})
    return original_read_text(self, *args, **kwargs)
pathlib.Path.read_text = mock_read_text

import pandas as pd
def mock_read_csv(*args, **kwargs):
    # Return a fake dataframe for claim_events_clean.csv
    return pd.DataFrame({
        'member_id': ['case_1'],
        'start_date': [pd.Timestamp('2023-05-01')],
        'ed_candidate_flag': [1],
        'encounter_type': ['OUTPATIENT']
    })
pd.read_csv = mock_read_csv

sys.path.insert(0, r'd:\cognizant-hackathon-main')
import backend.main
from fastapi.testclient import TestClient

def mock_kg_case(case_id):
    return {'ed_visits_90d': 4, 'outpatient_visits_90d': 0, 'index_date': '2023-01-01'}, []

backend.main.kg_case = mock_kg_case
app = backend.main.app
client = TestClient(app)
headers = {"x-api-key": "change-me"}

def _get_review_id(safety_status='NO_EMERGENCY_INDICATOR'):
    # Build up the whole chain explicitly
    import sqlite3
    db_path = backend.main.DB
    with sqlite3.connect(db_path) as c:
        sid = str(uuid.uuid4())
        c.execute("INSERT INTO safety_sessions(session_id,case_id,patient_id,attempt_count,current_context,safety_status,created_at,updated_at) VALUES (?, 'case_1', 'pat_1', 1, '{}', ?, 'now', 'now')", (sid, safety_status))
        oid = str(uuid.uuid4())
        c.execute("INSERT INTO opportunity_sessions(opportunity_id,safety_session_id,case_id,opportunity_level,opportunity_score,drivers,evidence,created_at) VALUES (?, ?, 'case_1', 'HIGH', 100, '[]', '{}', 'now')", (oid, sid))
        did = str(uuid.uuid4())
        c.execute("INSERT INTO driver_sessions(driver_session_id,opportunity_session_id,case_id,driver_status,drivers,summary,created_at) VALUES (?, ?, 'case_1', 'SUPPORTED', '[]', '', 'now')", (did, oid))
        pid = str(uuid.uuid4())
        c.execute("INSERT INTO pathway_sessions(pathway_session_id,driver_session_id,case_id,recommended_pathway,alternative_pathways,supporting_drivers,reason,created_at) VALUES (?, ?, 'case_1', 'PRIMARY_CARE', '[]', '[]', '', 'now')", (pid, did))
        prid = str(uuid.uuid4())
        c.execute("INSERT INTO provider_sessions(provider_session_id,pathway_session_id,case_id,recommended_pathway,providers,created_at) VALUES (?, ?, 'case_1', 'PRIMARY_CARE', '[]', 'now')", (prid, pid))
        revid = str(uuid.uuid4())
        c.execute("INSERT INTO care_manager_reviews(review_id,provider_session_id,case_id,reviewer_id,decision,original_pathway,original_provider_id,modified_pathway,modified_provider_id,reason,created_at) VALUES (?, ?, 'case_1', 'rev1', 'APPROVE', 'PRIMARY_CARE', '', '', '', '', 'now')", (revid, prid))
    return revid

def test_feedback_loop():
    revid = _get_review_id()
    
    # 1. Test Intervention Idempotency
    res1 = client.post('/v1/interventions', headers=headers, json={"review_id": revid})
    assert res1.status_code == 200
    iid1 = res1.json()['intervention_id']
    
    res2 = client.post('/v1/interventions', headers=headers, json={"review_id": revid})
    assert res2.status_code == 200
    iid2 = res2.json()['intervention_id']
    
    assert iid1 == iid2, "Intervention ID should be identical due to idempotency"
    
    # Verify INTERVENTION was written to member_history ONCE
    import sqlite3
    with sqlite3.connect(backend.main.DB) as c:
        rows = c.execute("SELECT * FROM member_history WHERE source=?", (f"intervention_id:{iid1}",)).fetchall()
        assert len(rows) == 1, "Should only have exactly one INTERVENTION event in member_history"
        assert rows[0][2] == 'INTERVENTION'
        
    print("Test Intervention Idempotency Passed")
    
    # 2. Test Outcome Idempotency
    res3 = client.post(f'/v1/interventions/{iid1}/outcomes', headers=headers, json={"window_days": 90})
    assert res3.status_code == 200
    oid1_index = res3.json()['outcomes']['INDEX_ENCOUNTER']['outcome_id']
    oid1_post = res3.json()['outcomes']['POST_INTERVENTION']['outcome_id']
    
    res4 = client.post(f'/v1/interventions/{iid1}/outcomes', headers=headers, json={"window_days": 90})
    assert res4.status_code == 200
    oid2_index = res4.json()['outcomes']['INDEX_ENCOUNTER']['outcome_id']
    oid2_post = res4.json()['outcomes']['POST_INTERVENTION']['outcome_id']
    
    assert oid1_index == oid2_index, "Outcome ID for INDEX_ENCOUNTER should be identical"
    assert oid1_post == oid2_post, "Outcome ID for POST_INTERVENTION should be identical"
    
    # Verify OUTCOME was written to member_history
    with sqlite3.connect(backend.main.DB) as c:
        rows = c.execute("SELECT * FROM member_history WHERE source=?", (f"outcome_id:{oid1_index}",)).fetchall()
        assert len(rows) == 1, "Should only have exactly one OUTCOME event for index"
        assert rows[0][2] == 'OUTCOME'
        
        rows2 = c.execute("SELECT * FROM member_history WHERE source=?", (f"outcome_id:{oid1_post}",)).fetchall()
        assert len(rows2) == 1, "Should only have exactly one OUTCOME event for post_intervention"
        assert rows2[0][2] == 'OUTCOME'
        
    print("Test Outcome Idempotency Passed")
    print("All Feedback Loop Tests Passed!")

if __name__ == '__main__':
    test_feedback_loop()
