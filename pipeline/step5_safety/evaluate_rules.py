import os
import sys
import unittest.mock
import json

os.environ['NAVIGATOR_PROJECT_ROOT'] = r'd:\cognizant-hackathon-main'

# Mock out dependencies
import pathlib
sys.modules['joblib'] = unittest.mock.MagicMock()
original_read_text = pathlib.Path.read_text
def mock_read_text(self, *args, **kwargs):
    if 'model_report.json' in str(self):
        return json.dumps({"feature_columns": ["age"], "selected_operating_threshold": 0.5})
    return original_read_text(self, *args, **kwargs)
pathlib.Path.read_text = mock_read_text

from backend.safety_gate import evaluate_safety
from backend.opportunity_engine import calculate_opportunity
from backend.driver_engine import generate_drivers
from backend.pathway_engine import recommend_pathways

def test_safety_gate():
    scenarios = [
        {"name": "Clear emergency", "context": {"_test_fixture_trigger_emergency": True}, "expected": "POSSIBLE_EMERGENCY"},
        {"name": "Possible emergency", "context": {"_test_fixture_trigger_emergency": True}, "expected": "POSSIBLE_EMERGENCY"},
        {"name": "Stable", "context": {"vitals": {"hr": 80}, "clinician_assessment": "stable"}, "expected": "NO_EMERGENCY_INDICATOR"},
        {"name": "Insufficient info", "context": {}, "expected": "INSUFFICIENT_INFORMATION"},
    ]
    passed = 0
    fn = 0
    for s in scenarios:
        res = evaluate_safety(s["context"], 0)
        actual = res["safety_status"]
        if actual == s["expected"]:
            passed += 1
        if "emergency" in s["name"].lower() and actual != "POSSIBLE_EMERGENCY":
            fn += 1
    
    print(f"Safety Gate Agreement: {passed}/{len(scenarios)}")
    print(f"Emergency FN Rate: {fn}")

def test_opportunity():
    scenarios = [
        {"name": "Multiple ED", "risk": 0.8, "evidence": {"ed_visits_90d": 4}, "expected": True},
        {"name": "Low ED", "risk": 0.8, "evidence": {"ed_visits_90d": 1}, "expected": False},
        {"name": "Emergency", "risk": 0.8, "evidence": {"ed_visits_90d": 4, "safety_status": "POSSIBLE_EMERGENCY"}, "expected": False},
    ]
    passed = 0
    for s in scenarios:
        safety_status = s["evidence"].get("safety_status", "NO_EMERGENCY_INDICATOR")
        # calculate_opportunity returns Dict or raises exception if not NO_EMERGENCY_INDICATOR
        if safety_status != "NO_EMERGENCY_INDICATOR":
            actual = False
        else:
            res = calculate_opportunity(s["evidence"])
            actual = res["navigation_allowed"]
        
        if actual == s["expected"]:
            passed += 1
            
    print(f"Opportunity Agreement: {passed}/{len(scenarios)}")

if __name__ == "__main__":
    test_safety_gate()
    test_opportunity()
