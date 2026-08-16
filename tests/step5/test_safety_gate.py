import os
from pathlib import Path
import json

os.environ['NAVIGATOR_PROJECT_ROOT'] = r'd:\cognizant-hackathon-main'
import sys
import unittest.mock as mock

mock_joblib = mock.MagicMock()
mock_joblib.load.return_value = mock.MagicMock()
sys.modules['joblib'] = mock_joblib

def mock_read_text(*args, **kwargs):
    if 'model_report.json' in str(args[0]):
        return '{"feature_columns": ["age"], "selected_operating_threshold": 0.5}'
    return args[0].read_text_original(*args[1:], **kwargs)

Path.read_text_original = Path.read_text
Path.read_text = mock_read_text

sys.path.insert(0, r'd:\cognizant-hackathon-main')

import backend.main
def mock_kg_case(case_id):
    return {'risk_band': 'HIGH', 'index_date': '2023-01-01'}, ['No outpatient']
backend.main.kg_case = mock_kg_case

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
headers = {'X-API-Key': 'change-me'}

def test_safety_gate():
    # TEST 1: Possible emergency
    resp1 = client.post('/v1/safety/assess', headers=headers, json={
        "case_id": "test_case_1",
        "patient_id": "test_patient_1",
        "new_context": {"_test_fixture_trigger_emergency": True}
    })
    assert resp1.status_code == 200, resp1.text
    res1 = resp1.json()
    assert res1['safety_status'] == 'POSSIBLE_EMERGENCY'
    assert res1['navigation_allowed'] is False
    assert res1['human_review_required'] is True
    print("TEST 1 Passed")
    
    # TEST 2: Sufficient info, no emergency
    resp2 = client.post('/v1/safety/assess', headers=headers, json={
        "case_id": "test_case_2",
        "patient_id": "test_patient_2",
        "new_context": {"_test_fixture_sufficient_info": True}
    })
    res2 = resp2.json()
    assert res2['safety_status'] == 'NO_EMERGENCY_INDICATOR'
    assert res2['navigation_allowed'] is True
    print("TEST 2 Passed")
    
    # TEST 3: Missing information
    resp3 = client.post('/v1/safety/assess', headers=headers, json={
        "case_id": "test_case_3",
        "patient_id": "test_patient_3",
        "new_context": {}
    })
    res3 = resp3.json()
    assert res3['safety_status'] == 'INSUFFICIENT_INFORMATION'
    assert res3['navigation_allowed'] is False
    assert res3['action_required'] == 'REQUEST_INFORMATION'
    assert 'missing_information' in res3
    print("TEST 3 Passed")
    
    # TEST 4: Missing info -> user provides required info
    sid4 = res3['session_id']
    resp4 = client.post('/v1/safety/assess', headers=headers, json={
        "session_id": sid4,
        "case_id": "test_case_3",
        "patient_id": "test_patient_3",
        "new_context": {"_test_fixture_sufficient_info": True}
    })
    res4 = resp4.json()
    assert res4['safety_status'] == 'NO_EMERGENCY_INDICATOR'
    assert res4['navigation_allowed'] is True
    print("TEST 4 Passed")
    
    # TEST 5: Missing info -> still insufficient -> escalates
    resp5_1 = client.post('/v1/safety/assess', headers=headers, json={
        "case_id": "test_case_5",
        "patient_id": "test_patient_5",
        "new_context": {}
    })
    sid5 = resp5_1.json()['session_id']
    resp5_2 = client.post('/v1/safety/assess', headers=headers, json={
        "session_id": sid5,
        "case_id": "test_case_5",
        "patient_id": "test_patient_5",
        "new_context": {}
    })
    resp5_3 = client.post('/v1/safety/assess', headers=headers, json={
        "session_id": sid5,
        "case_id": "test_case_5",
        "patient_id": "test_patient_5",
        "new_context": {}
    })
    res5 = resp5_3.json()
    assert res5['safety_status'] == 'INSUFFICIENT_INFORMATION'
    assert res5['action_required'] == 'HUMAN_CLINICAL_REVIEW'
    print("TEST 5 Passed")
    
    # TEST 6: Info provided reveals possible emergency
    resp6_1 = client.post('/v1/safety/assess', headers=headers, json={
        "case_id": "test_case_6",
        "patient_id": "test_patient_6",
        "new_context": {}
    })
    sid6 = resp6_1.json()['session_id']
    resp6_2 = client.post('/v1/safety/assess', headers=headers, json={
        "session_id": sid6,
        "case_id": "test_case_6",
        "patient_id": "test_patient_6",
        "new_context": {"_test_fixture_trigger_emergency": True}
    })
    res6 = resp6_2.json()
    assert res6['safety_status'] == 'POSSIBLE_EMERGENCY'
    assert res6['action_required'] == 'STOP_NAVIGATION'
    print("TEST 6 Passed")

    # TEST 7: Valid NO_EMERGENCY_INDICATOR session -> pathway allowed
    resp7 = client.post('/v1/safety/assess', headers=headers, json={
        "case_id": "case_valid",
        "patient_id": "patient_valid",
        "new_context": {"_test_fixture_sufficient_info": True}
    })
    sid_valid = resp7.json()['session_id']
    opp7 = client.post('/v1/navigation-opportunity', headers=headers, json={
        "case_id": "case_valid", "safety_session_id": sid_valid
    })
    opp_id_valid = opp7.json()['opportunity_id']
    drv7 = client.post('/v1/navigation-drivers', headers=headers, json={
        "case_id": "case_valid", "opportunity_session_id": opp_id_valid
    })
    drv_id_valid = drv7.json()['driver_session_id']
    resp7_pathway = client.post('/v1/pathways', headers=headers, json={
        "case_id": "case_valid",
        "reviewer_id": "reviewer_1",
        "driver_session_id": drv_id_valid,
        "reviewer_cleared": True
    })
    assert resp7_pathway.json()['status'] == 'CARE_MANAGER_REVIEW'
    print("TEST 7 Passed")

    # TEST 8: POSSIBLE_EMERGENCY session -> pathway blocked (opportunity endpoint blocks it)
    resp8 = client.post('/v1/safety/assess', headers=headers, json={
        "case_id": "case_em",
        "patient_id": "patient_em",
        "new_context": {"_test_fixture_trigger_emergency": True}
    })
    sid_em = resp8.json()['session_id']
    opp8 = client.post('/v1/navigation-opportunity', headers=headers, json={
        "case_id": "case_em", "safety_session_id": sid_em
    })
    assert opp8.status_code == 400
    print("TEST 8 Passed")

    # TEST 9: INSUFFICIENT_INFORMATION session -> pathway blocked (opportunity blocks)
    resp9 = client.post('/v1/safety/assess', headers=headers, json={
        "case_id": "case_ins",
        "patient_id": "patient_ins",
        "new_context": {}
    })
    sid_ins = resp9.json()['session_id']
    opp9 = client.post('/v1/navigation-opportunity', headers=headers, json={
        "case_id": "case_ins", "safety_session_id": sid_ins
    })
    assert opp9.status_code == 400
    print("TEST 9 Passed")

    # TEST 10: Client attempts to downgrade POSSIBLE_EMERGENCY to NO_EMERGENCY_INDICATOR -> blocked
    # Cannot be tested the same way anymore since pathways doesn't take safety_status, 
    # but the old test is equivalent to bypassing driver session
    resp10_pathway = client.post('/v1/pathways', headers=headers, json={
        "case_id": "case_em",
        "reviewer_id": "reviewer_1",
        "driver_session_id": None,
        "safety_status": "NO_EMERGENCY_INDICATOR",
        "reviewer_cleared": True
    })
    assert resp10_pathway.json()['status'] == 'CLINICAL_REVIEW_REQUIRED'
    print("TEST 10 Passed")

    # TEST 11: Client attempts to downgrade INSUFFICIENT_INFORMATION to NO_EMERGENCY_INDICATOR -> blocked
    resp11_pathway = client.post('/v1/pathways', headers=headers, json={
        "case_id": "case_ins",
        "reviewer_id": "reviewer_1",
        "driver_session_id": None,
        "safety_status": "NO_EMERGENCY_INDICATOR",
        "reviewer_cleared": True
    })
    assert resp11_pathway.json()['status'] == 'CLINICAL_REVIEW_REQUIRED'
    print("TEST 11 Passed")

    # TEST 12: Client attempts to upgrade NO_EMERGENCY_INDICATOR to POSSIBLE_EMERGENCY -> server result remains authoritative
    # (Since it's NO_EMERGENCY_INDICATOR on server, pathway is allowed despite client passing POSSIBLE_EMERGENCY)
    resp12_pathway = client.post('/v1/pathways', headers=headers, json={
        "case_id": "case_valid",
        "reviewer_id": "reviewer_1",
        "driver_session_id": drv_id_valid,
        "safety_status": "POSSIBLE_EMERGENCY",
        "reviewer_cleared": True
    })
    assert resp12_pathway.json()['status'] == 'CARE_MANAGER_REVIEW'
    print("TEST 12 Passed")

    # TEST 13: Missing driver session -> blocked
    resp13_pathway = client.post('/v1/pathways', headers=headers, json={
        "case_id": "case_valid",
        "reviewer_id": "reviewer_1",
        "safety_status": "NO_EMERGENCY_INDICATOR",
        "reviewer_cleared": True
    })
    assert resp13_pathway.json()['status'] == 'CLINICAL_REVIEW_REQUIRED'
    assert 'Missing driver session' in resp13_pathway.json()['reason']
    print("TEST 13 Passed")

    # TEST 14: Invalid driver session -> blocked
    resp14_pathway = client.post('/v1/pathways', headers=headers, json={
        "case_id": "case_valid",
        "reviewer_id": "reviewer_1",
        "driver_session_id": "fake_session",
        "reviewer_cleared": True
    })
    assert resp14_pathway.json()['status'] == 'CLINICAL_REVIEW_REQUIRED'
    assert 'mismatched driver session' in resp14_pathway.json()['reason']
    print("TEST 14 Passed")

    # TEST 15: Driver session belonging to another patient/case -> blocked
    resp15_pathway = client.post('/v1/pathways', headers=headers, json={
        "case_id": "different_case",
        "reviewer_id": "reviewer_1",
        "driver_session_id": drv_id_valid,
        "reviewer_cleared": True
    })
    assert resp15_pathway.json()['status'] == 'CLINICAL_REVIEW_REQUIRED'
    assert 'mismatched driver session' in resp15_pathway.json()['reason']
    print("TEST 15 Passed")

    print("All Safety Gate Authority Tests Passed!")

if __name__ == "__main__":
    test_safety_gate()
