import os
import sys
import joblib
import pandas as pd
import numpy as np
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from safety_gate_engine import SafetyGateEngine

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../pipeline/step7_provider')))
from advanced_provider_matching_engine import AdvancedProviderMatchingEngine
from provider_matching_engine import ProviderMatchingPrototype

app = FastAPI(title="UC07 Care Manager Orchestrator - REAL DATA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STEP4_MODEL = None
SAFETY_GATE = None

def init_services():
    global STEP4_MODEL, SAFETY_GATE
    
    # 1. Load Step 4 Model
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'models/UC07_SYNTHEA_STEP4_BEST_MODEL.joblib'))
    try:
        STEP4_MODEL = joblib.load(model_path)
        print("Loaded Step 4 Model.")
    except Exception as e:
        print(f"Error loading Step 4 model: {e}")
        
    # 2. Init Step 5 Safety Gate
    try:
        SAFETY_GATE = SafetyGateEngine()
        print("Loaded Safety Gate.")
    except Exception as e:
        print(f"Error loading Safety Gate: {e}")

init_services()

class PatientEvalRequest(BaseModel):
    patient_id: str
    encounter_id: str
    clinical_context: Dict[str, Any]

class DecisionAuditRequest(BaseModel):
    patient_id: str
    encounter_id: str
    reviewer_id: str
    action: str  # APPROVE, MODIFY, REJECT, ESCALATE
    reason: str
    system_pathway: str
    system_provider: str
    selected_provider: str

def compute_care_pathway(risk_band: str, safety_status: str) -> dict:
    if safety_status == 'RED':
        return {"Pathway": "P1", "Name": "Emergency / Immediate Clinical Evaluation", "Reason": "RED safety status overrides all risk."}
    if safety_status == 'YELLOW':
        return {"Pathway": "P2", "Name": "Urgent Clinician Review", "Reason": "YELLOW safety status requires immediate human clinician evaluation."}
    if safety_status == 'GREEN':
        if risk_band == 'HIGH':
            return {"Pathway": "P3", "Name": "Priority Outpatient Follow-up", "Reason": "GREEN safety but HIGH historical repeat-ED risk."}
        elif risk_band == 'MEDIUM':
            return {"Pathway": "P4", "Name": "Routine Outpatient Follow-up", "Reason": "GREEN safety and MEDIUM risk."}
        else:
            return {"Pathway": "P5", "Name": "Preventive / Routine Care Management", "Reason": "GREEN safety and LOW risk."}
    return {"Pathway": "UNKNOWN", "Name": "Unknown", "Reason": "Unmapped logic state"}

def get_real_patient_features(patient_id: str, encounter_id: str) -> pd.DataFrame:
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data/patient_features.db'))
    if not os.path.exists(db_path):
        return None
    try:
        conn = sqlite3.connect(db_path)
        query = f"SELECT * FROM patient_features WHERE PATIENT_ID = ? AND ENCOUNTER_ID = ? LIMIT 1"
        df = pd.read_sql_query(query, conn, params=(patient_id, encounter_id))
        conn.close()
        return df if not df.empty else None
    except:
        return None

def get_real_providers_by_specialty(specialty: str) -> pd.DataFrame:
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data/provider_index.db'))
    if not os.path.exists(db_path):
        return None
    try:
        conn = sqlite3.connect(db_path)
        # We join dac and scores. Utilization and facilities omit as per audit.
        query = """
            SELECT 
                d.NPI, 
                d.PAC_ID, 
                d.First_Name || ' ' || d.Last_Name AS Name, 
                d.Specialty, 
                COALESCE(s.Quality_Score, 50) AS Norm_Quality
            FROM dac d
            LEFT JOIN scores s ON d.NPI = s.NPI
            WHERE d.Specialty LIKE ?
            LIMIT 500
        """
        df = pd.read_sql_query(query, conn, params=('%' + specialty + '%',))
        conn.close()
        
        return df if not df.empty else None
    except Exception as e:
        print(f"Provider DB Error: {e}")
        return None

@app.post("/api/evaluate")
def evaluate_patient(req: PatientEvalRequest):
    # STEP 4: Historical Risk
    if not STEP4_MODEL:
        raise HTTPException(status_code=500, detail="MODEL_ERROR: Step 4 model unavailable.")
        
    df_patient = get_real_patient_features(req.patient_id, req.encounter_id)
    if df_patient is None:
        return {"error": "DATA_UNAVAILABLE", "message": f"No historical features found for patient {req.patient_id} and encounter {req.encounter_id}"}
        
    try:
        expected_features = list(STEP4_MODEL.feature_names_in_)
        X = df_patient[expected_features]
        
        prob = STEP4_MODEL.predict_proba(X)[0][1]
        
        drivers = []
        if hasattr(STEP4_MODEL, 'calibrated_classifiers_'):
            est = STEP4_MODEL.calibrated_classifiers_[0].estimator[-1]
            if hasattr(est, 'feature_importances_'):
                importances = est.feature_importances_
                top_indices = np.argsort(importances)[-3:][::-1]
                for idx in top_indices:
                    drivers.append(f"{expected_features[idx]} (importance: {importances[idx]})")
                    
        if prob > 0.6: risk_band = "HIGH"
        elif prob > 0.3: risk_band = "MEDIUM"
        else: risk_band = "LOW"
        
        step4_result = {
            "score": round(prob, 3),
            "band": risk_band,
            "drivers": drivers if drivers else ["Feature importances unavailable"],
            "provenance": f"REAL MODEL PREDICTION: PATIENT_ID={req.patient_id}, ENCOUNTER_ID={req.encounter_id}, INDEX_TIMESTAMP={df_patient['INDEX_TIMESTAMP'].iloc[0]}"
        }
    except Exception as e:
        print(f"Step 4 failed: {e}")
        return {"error": "MODEL_ERROR", "message": str(e)}

    # STEP 5: Safety Gate
    if not SAFETY_GATE:
        return {"error": "SAFETY_REVIEW_REQUIRED", "message": "Safety Gate engine offline."}
        
    try:
        safety_output = SAFETY_GATE.evaluate(req.clinical_context)
        safety_status = safety_output.get('Status', 'GREEN')
        report = safety_output.get('Reason', '') + ' | ' + safety_output.get('Supporting data', '')
        triggered_rules = [{"rule_id": safety_output.get('Triggered Rule'), "reason": safety_output.get('Reason')}] if safety_output.get('Triggered Rule') != 'None' else []
    except Exception as e:
        print(f"Step 5 failed: {e}")
        return {"error": "SAFETY_REVIEW_REQUIRED", "message": str(e)}

    # STEP 6: Care Pathway Matrix
    pathway_result = compute_care_pathway(risk_band, safety_status)
    req_specialty = "Cardiology" if req.clinical_context.get("required_specialty_hint") == "Cardiology" else "General Practice"

    # STEP 7: Provider Matching
    df_providers = get_real_providers_by_specialty(req_specialty)
    if df_providers is None:
        return {"error": "NO_PROVIDER_MATCH", "message": f"No providers found in real Cognizant dataset for specialty: {req_specialty}"}

    provider_engine = AdvancedProviderMatchingEngine(df_providers)
    
    patient_match_state = {
        "Safety Status": safety_status,
        "Pathway": pathway_result["Pathway"],
        "Required Specialty": req_specialty,
        "Clinical Context": req.clinical_context,
        "Conditions": ", ".join(drivers) if 'drivers' in locals() else "",
        "Clinician Cleared": False 
    }
    
    provider_result = provider_engine.match(patient_match_state)
    
    # Append provenance to the top options is now natively handled by AdvancedProviderMatchingEngine

    return {
        "patient_id": req.patient_id,
        "encounter_id": req.encounter_id,
        "step4": step4_result,
        "step5": {
            "status": safety_status,
            "report": report,
            "rules": triggered_rules
        },
        "step6": pathway_result,
        "step7": provider_result
    }

@app.post("/api/audit")
def submit_audit(req: DecisionAuditRequest):
    audit_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../logs/UC07_CARE_MANAGER_AUDIT_TRAIL.csv'))
    import csv
    from datetime import datetime
    file_exists = os.path.isfile(audit_file)
    with open(audit_file, 'a', newline='') as csvfile:
        fieldnames = ['timestamp', 'patient_id', 'encounter_id', 'reviewer_id', 'action', 'reason', 'system_pathway', 'system_provider', 'selected_provider']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            'timestamp': datetime.utcnow().isoformat(),
            'patient_id': req.patient_id,
            'encounter_id': req.encounter_id,
            'reviewer_id': req.reviewer_id,
            'action': req.action,
            'reason': req.reason,
            'system_pathway': req.system_pathway,
            'system_provider': req.system_provider,
            'selected_provider': req.selected_provider
        })
    return {"status": "success", "message": "Audit recorded."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
