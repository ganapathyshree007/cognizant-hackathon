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

sys.path.insert(0, r'd:\cognizant-hackathon-main')
import backend.main
from fastapi.testclient import TestClient

def mock_kg_case(case_id):
    if case_id == 'case_primary':
        return {'ed_visits_90d': 4, 'outpatient_visits_90d': 0}, []
    elif case_id == 'case_urgent':
        return {'days_since_latest_ed': 3, 'ed_visits_90d': 2, 'outpatient_visits_90d': 2, 'risk_score': 0.8}, []
    elif case_id == 'case_care_management':
        return {'ed_visits_90d': 4, 'outpatient_visits_90d': 0, 'chronic_condition_burden': 4}, []
    elif case_id == 'case_em':
        return {}, []
    elif case_id == 'case_single_ed':
        return {'ed_visits_90d': 1}, []
    return {'ed_visits_90d': 4, 'outpatient_visits_90d': 0}, []

backend.main.kg_case = mock_kg_case
app = backend.main.app
client = TestClient(app)
headers = {"x-api-key": "change-me"}

def _get_chain(case_id, safety_context={"_test_fixture_sufficient_info": True}, telehealth=False):
    resp1 = client.post('/v1/safety/assess', headers=headers, json={"case_id": case_id, "patient_id": "pat_1", "new_context": safety_context})
    sid_safe = resp1.json()['session_id']
    if resp1.json()['safety_status'] != 'NO_EMERGENCY_INDICATOR':
        return sid_safe, None, None, None
        
    res_opp = client.post('/v1/navigation-opportunity', headers=headers, json={"case_id": case_id, "safety_session_id": sid_safe})
    opp_id = res_opp.json()['opportunity_id']
    
    res_drv = client.post('/v1/navigation-drivers', headers=headers, json={"case_id": case_id, "opportunity_session_id": opp_id})
    drv_id = res_drv.json()['driver_session_id']
    
    res_path = client.post('/v1/pathways', headers=headers, json={"case_id": case_id, "reviewer_id": "rev1", "driver_session_id": drv_id, "reviewer_cleared": True, "telehealth_preferred": telehealth})
    path_id = res_path.json().get('pathway_session_id')
    
    return sid_safe, opp_id, drv_id, path_id

def test_step9_providers():
    _, _, _, path_primary = _get_chain('case_primary')
    _, _, _, path_urgent = _get_chain('case_urgent')
    _, _, _, path_care = _get_chain('case_care_management')
    _, _, _, path_tele = _get_chain('case_primary', telehealth=True)
    
    # 1. PRIMARY_CARE
    res1 = client.post('/v1/providers/recommend', headers=headers, json={'pathway_session_id': path_primary})
    assert res1.status_code == 200
    assert res1.json()['recommended_pathway'] == 'PRIMARY_CARE'
    assert any('Primary Care' in p['provider_name'] for p in res1.json()['provider_results'])
    
    # 2. URGENT_CARE
    res2 = client.post('/v1/providers/recommend', headers=headers, json={'pathway_session_id': path_urgent})
    assert res2.json()['recommended_pathway'] == 'URGENT_CARE'
    assert any(p['facility_id'] for p in res2.json()['provider_results'])
    assert all(p['provider_id'] is None for p in res2.json()['provider_results'])
    
    # 3. TELEHEALTH
    res3 = client.post('/v1/providers/recommend', headers=headers, json={'pathway_session_id': path_tele})
    # Since TELEHEALTH is alternative, pathway in the session is still PRIMARY_CARE for case_primary? Wait!
    # If the pathway_session gave PRIMARY_CARE as recommended_pathway, res3 will give PRIMARY_CARE.
    # To test TELEHEALTH, we need a pathway where telehealth was the recommended pathway, or we use require_telehealth=True
    res3b = client.post('/v1/providers/recommend', headers=headers, json={'pathway_session_id': path_primary, 'require_telehealth': True})
    assert all(p['telehealth_available'] == 'YES' for p in res3b.json()['provider_results'])
    
    # 4. CARE_MANAGEMENT
    res4 = client.post('/v1/providers/recommend', headers=headers, json={'pathway_session_id': path_care})
    assert res4.json()['recommended_pathway'] == 'CARE_MANAGEMENT'
    assert any('Care Manager' in p['provider_name'] for p in res4.json()['provider_results'])
    
    # 5. & 6. POSSIBLE EMERGENCY / INSUFFICIENT INFO
    # We must mock a pathway session pointing to an emergency safety session
    import sqlite3
    db_path = backend.main.DB
    with sqlite3.connect(db_path) as c:
        pid = str(uuid.uuid4())
        # create a safety session with POSSIBLE_EMERGENCY
        sid = str(uuid.uuid4())
        c.execute("INSERT INTO safety_sessions(session_id,case_id,patient_id,attempt_count,current_context,safety_status,created_at,updated_at) VALUES (?, 'case_em', 'pat_1', 1, '{}', 'POSSIBLE_EMERGENCY', 'now', 'now')", (sid,))
        oid = str(uuid.uuid4())
        c.execute("INSERT INTO opportunity_sessions(opportunity_id,safety_session_id,case_id,opportunity_level,opportunity_score,drivers,evidence,created_at) VALUES (?, ?, 'case_em', 'HIGH', 100, '[]', '{}', 'now')", (oid, sid))
        did = str(uuid.uuid4())
        c.execute("INSERT INTO driver_sessions(driver_session_id,opportunity_session_id,case_id,driver_status,drivers,summary,created_at) VALUES (?, ?, 'case_em', 'SUPPORTED', '[]', '', 'now')", (did, oid))
        c.execute("INSERT INTO pathway_sessions(pathway_session_id,driver_session_id,case_id,recommended_pathway,alternative_pathways,supporting_drivers,reason,created_at) VALUES (?, ?, 'case_em', 'PRIMARY_CARE', '[]', '[]', '', 'now')", (pid, did))
        
    res5 = client.post('/v1/providers/recommend', headers=headers, json={'pathway_session_id': pid})
    assert res5.json()['provider_results'] == []
    assert 'blocked' in res5.json()['reason']

    # 7. & 8. Client fake pathway / provider - handled because endpoint only takes pathway_session_id
    
    # 9. Pathway session mismatch (404)
    res9 = client.post('/v1/providers/recommend', headers=headers, json={'pathway_session_id': 'fake-session'})
    assert res9.status_code == 404
    
    # 11. No location -> No distance
    assert 'distance' not in res1.json()['provider_results'][0]
    
    # 12. No matching provider
    res12 = client.post('/v1/providers/recommend', headers=headers, json={'pathway_session_id': path_primary, 'state': 'ZZ'})
    assert res12.json()['provider_results'] == []
    assert res12.json()['reason'] == 'NO_PROVIDER_FOUND'
    
    # 14. Availability
    assert res1.json()['availability_status'] == 'NOT_VERIFIED'
    
    # 15. Network
    assert res1.json()['network_status'] == 'NOT_VERIFIED'
    
    print("All Step 9 tests passed!")

if __name__ == '__main__':
    test_step9_providers()
