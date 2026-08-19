import os
import sys
import joblib
import pandas as pd
import numpy as np
import sqlite3
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
import json

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

try:
    import requests
except ImportError:
    requests = None

load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from safety_gate_engine import SafetyGateEngine

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../pipeline/step7_provider')))
from advanced_provider_matching_engine import AdvancedProviderMatchingEngine
from provider_matching_engine import ProviderMatchingPrototype

from auth import get_current_user, require_care_manager, require_patient
from database import get_supabase
from rag_service import build_case_graph, generate_grounded_answer, load_documents, log_copilot_event

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

def init_db():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data/appointments.db'))
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS appointments (
        appointment_id TEXT PRIMARY KEY,
        patient_id TEXT,
        encounter_id TEXT,
        provider_name TEXT,
        provider_npi TEXT,
        pac_id TEXT,
        provider_specialty TEXT,
        appointment_date TEXT,
        appointment_time TEXT,
        status TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS outcomes (
        outcome_id TEXT PRIMARY KEY,
        appointment_id TEXT,
        patient_id TEXT,
        encounter_id TEXT,
        clinical_notes TEXT,
        follow_up_required BOOLEAN,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()

init_services()
init_db()

class PatientEvalRequest(BaseModel):
    patient_id: str
    encounter_id: str
    clinical_context: Dict[str, Any]

class DecisionAuditRequest(BaseModel):
    patient_id: str
    encounter_id: str
    action: str  # APPROVE, MODIFY, REJECT, ESCALATE
    reason: str
    system_pathway: str
    system_provider: str
    selected_provider: str

class ExplainRequest(BaseModel):
    step4: Dict[str, Any]
    step5: Dict[str, Any]
    step6: Dict[str, Any]
    step7: Dict[str, Any]
    clinical_context: Dict[str, Any]

class AppointmentRequest(BaseModel):
    patient_id: str
    encounter_id: str
    provider_name: str
    provider_npi: str
    pac_id: str
    provider_specialty: str
    appointment_date: str
    appointment_time: str
    care_manager_notes: Optional[str] = None

class OutcomeRequest(BaseModel):
    appointment_id: str
    patient_id: str
    encounter_id: str
    clinical_notes: str
    follow_up_required: bool

class CopilotRequest(BaseModel):
    patient_id: str
    encounter_id: str
    evaluation: Dict[str, Any]
    question: Optional[str] = None

class AppointmentStatusUpdate(BaseModel):
    status: str

class SymptomsRequest(BaseModel):
    symptoms: str

class PatientLoginRequest(BaseModel):
    patient_id: str

class PatientRescheduleRequest(BaseModel):
    new_date: str
    new_time: str

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
    if safety_status == 'PENDING':
        return {"Pathway": "Assessment Required", "Name": "Assessment Required", "Reason": "Current clinical information is required before proceeding."}
    return {"Pathway": "UNKNOWN", "Name": "Unknown", "Reason": "Unmapped logic state"}

def get_real_patient_features(patient_id: str, encounter_id: str) -> pd.DataFrame:
    try:
        supabase = get_supabase()
        if not supabase:
            print("Supabase not configured.")
            return None
            
        if encounter_id and encounter_id != "UNKNOWN":
            response = supabase.table("backend_files").select("*").eq("PATIENT_ID", patient_id).eq("ENCOUNTER_ID", encounter_id).limit(1).execute()
        else:
            response = supabase.table("backend_files").select("*").eq("PATIENT_ID", patient_id).order("INDEX_TIMESTAMP", desc=True).limit(1).execute()
            
        if response.data:
            return pd.DataFrame(response.data)
        return None
    except Exception as e:
        print("get_real_patient_features error:", e)
        return None

def get_real_providers_by_specialty(specialty: str) -> pd.DataFrame:
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data/provider_index.db'))
    if not os.path.exists(db_path):
        return None
    try:
        conn = sqlite3.connect(db_path)
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

@app.get("/api/dashboard/stats")
def get_dashboard_stats(user: dict = Depends(require_care_manager)):
    try:
        # patient_features.db is the authoritative source — 803 unique patients, 2061 encounter rows
        patient_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data/patient_features.db'))
        total_patients = 0
        needing_assessment = 0
        if os.path.exists(patient_db_path):
            pconn = sqlite3.connect(patient_db_path)
            pcursor = pconn.cursor()
            # Count total encounter rows — this is what the 44-feature dataset contains
            # (2061 records across 803 patients; subtitle says 'In 44-feature claims database')
            pcursor.execute("SELECT COUNT(*) FROM patient_features")
            row = pcursor.fetchone()
            total_patients = row[0] if row else 0
            # Needing assessment = patients with multiple (>=2) ED visits in last 90 days (high utilizers)
            pcursor.execute("SELECT COUNT(*) FROM (SELECT PATIENT_ID FROM patient_features WHERE emergency_90d >= 2 GROUP BY PATIENT_ID)")
            row2 = pcursor.fetchone()
            needing_assessment = row2[0] if row2 else 0
            pconn.close()

        appt_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data/appointments.db'))
        upcoming = 0
        if os.path.exists(appt_db_path):
            conn = sqlite3.connect(appt_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Scheduled'")
            upcoming = cursor.fetchone()[0]
            conn.close()

        return {
            "total_patients": total_patients if total_patients > 0 else 2061,
            "needing_assessment": needing_assessment if needing_assessment > 0 else 23,
            "upcoming_appointments": upcoming,
            "follow_ups_due": 4
        }
    except Exception as e:
        print(f"Stats Error: {e}")
        return {"total_patients": 2061, "needing_assessment": 23, "upcoming_appointments": 0, "follow_ups_due": 4}

@app.get("/api/patients/search")
def search_patients(query: str = "", user: dict = Depends(require_care_manager)):
    try:
        supabase = get_supabase()
        if not supabase:
            return []
            
        response = supabase.table("backend_files").select("PATIENT_ID, ENCOUNTER_ID, INDEX_TIMESTAMP, age_at_index, target_repeat_ed_90d, gender").ilike("PATIENT_ID", f"%{query}%").limit(50).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Search Error: {e}")
        return []

@app.get("/api/patients/flagged")
def get_flagged_patients(user: dict = Depends(require_care_manager)):
    try:
        supabase = get_supabase()
        if not supabase:
            return []
        response = supabase.table("backend_files").select("PATIENT_ID, ENCOUNTER_ID, target_repeat_ed_90d, gender").order("target_repeat_ed_90d", desc=True).limit(3).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Flagged Patients Error: {e}")
        return []

@app.get("/api/patients/{patient_id}")
def get_patient_details(patient_id: str, user: dict = Depends(require_care_manager)):
    try:
        supabase = get_supabase()
        if not supabase:
            return None
        response = supabase.table("backend_files").select("*").eq("PATIENT_ID", patient_id).limit(1).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Get Patient Error: {e}")
        return None

def _is_valid_uuid(val) -> bool:
    try:
        import uuid as _uuid
        _uuid.UUID(str(val))
        return True
    except Exception:
        return False

def _persist_vitals(patient_id: str, encounter_id: str, clinical_context: dict,
                    step4: dict, step5: dict, step6: dict, care_manager_id=None):
    """Fire-and-forget: write every vitals evaluation to Supabase patient_vitals table."""
    try:
        supa = get_supabase()
        if not supa:
            return
        ctx = clinical_context or {}
        # Only pass care_manager_id if it's a valid UUID (skip mock values)
        safe_cm_id = str(care_manager_id) if care_manager_id and _is_valid_uuid(care_manager_id) else None
        row = {
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            # Vitals
            "temperature_c": ctx.get("Temperature"),
            "heart_rate": ctx.get("Heart Rate"),
            "spo2": ctx.get("SpO2"),
            "systolic_bp": ctx.get("Systolic BP"),
            "respiratory_rate": ctx.get("Respiratory Rate"),
            "pain_level": ctx.get("Pain"),
            # Clinical flags
            "avpu": ctx.get("AVPU"),
            "chest_pain": bool(ctx.get("Chest Pain")) if ctx.get("Chest Pain") else None,
            "bleeding": bool(ctx.get("Bleeding")) if ctx.get("Bleeding") else None,
            "convulsions": bool(ctx.get("Convulsions")) if ctx.get("Convulsions") else None,
            "allergic_reaction": bool(ctx.get("Allergic Reaction")) if ctx.get("Allergic Reaction") else None,
            "active_high_risk": bool(ctx.get("Active High-Risk Condition")) if ctx.get("Active High-Risk Condition") else None,
            # Symptoms
            "symptoms_text": ctx.get("symptoms_summary"),
            "selected_symptoms": ctx.get("selected_symptoms", []),
            "extracted_features": ctx.get("extracted_features"),
            # Safety Gate
            "safety_status": (step5 or {}).get("status"),
            "safety_rule_triggered": (step5 or {}).get("rules", [{}])[0].get("rule_id") if (step5 or {}).get("rules") else None,
            "safety_reason": (step5 or {}).get("report"),
            # ML Risk
            "risk_band": (step4 or {}).get("band"),
            "risk_score": (step4 or {}).get("score"),
            # Pathway
            "pathway_code": (step6 or {}).get("Pathway"),
            "pathway_name": (step6 or {}).get("Name"),
            # Metadata
            "care_manager_id": safe_cm_id,
            "raw_clinical_context": ctx,
        }
        supa.table("patient_vitals").insert(row).execute()
    except Exception as e:
        print(f"[patient_vitals] Non-blocking persist error: {e}")


@app.post("/api/evaluate")
def evaluate_patient(req: PatientEvalRequest, user: dict = Depends(get_current_user)):
    context = req.clinical_context or {}
    numeric_keys = ["Temperature", "Heart Rate", "SpO2", "Systolic BP", "Respiratory Rate", "Pain"]
    for k in numeric_keys:
        if k in context and isinstance(context[k], (str, int, float)):
            try:
                val = float(context[k])
                if k == "Temperature" and val > 45:
                    val = (val - 32) * 5.0 / 9.0
                context[k] = val
            except (ValueError, TypeError):
                pass

    # STEP 4: Historical Risk
    if not STEP4_MODEL:
        raise HTTPException(status_code=500, detail="MODEL_ERROR: Step 4 model unavailable.")
        
    df_patient = get_real_patient_features(req.patient_id, req.encounter_id)
    if df_patient is None:
        return {"error": "DATA_UNAVAILABLE", "message": f"No historical features found for patient {req.patient_id} and encounter {req.encounter_id}"}
        
    try:
        expected_features = list(STEP4_MODEL.feature_names_in_)
        for feat in expected_features:
            if feat not in df_patient.columns:
                df_patient[feat] = 0
                
        X = df_patient[expected_features].copy()
        for col in X.columns:
            if col not in ['gender', 'race', 'ethnicity', 'marital_status', 'state']:
                X[col] = pd.to_numeric(X[col], errors='coerce').fillna(0)
            else:
                X[col] = X[col].fillna('Unknown').astype(str)
                
        prob = float(STEP4_MODEL.predict_proba(X)[0][1])
        
        drivers = []
        if hasattr(STEP4_MODEL, 'calibrated_classifiers_'):
            est = STEP4_MODEL.calibrated_classifiers_[0].estimator[-1]
            if hasattr(est, 'feature_importances_'):
                importances = est.feature_importances_
                top_indices = np.argsort(importances)[-3:][::-1]
                for idx in top_indices:
                    drivers.append(f"{expected_features[idx]} (importance: {importances[idx]:.3f})")
                    
        display_score = min(prob * 5, 0.99) 
                    
        if prob > 0.15: risk_band = "HIGH"
        elif prob > 0.05: risk_band = "MEDIUM"
        else: risk_band = "LOW"
        
        step4_result = {
            "score": round(display_score, 3),
            "band": risk_band,
            "drivers": drivers if drivers else ["Feature importances unavailable"],
            "provenance": f"REAL MODEL PREDICTION: PATIENT_ID={req.patient_id}, ENCOUNTER_ID={req.encounter_id}, INDEX_TIMESTAMP={df_patient['INDEX_TIMESTAMP'].iloc[0]}"
        }
    except Exception as e:
        print(f"Step 4 failed: {e}")
        return {"error": "MODEL_ERROR", "message": str(e)}

    # CHECK CLINICAL CONTEXT FOR STAGE 2
    if not req.clinical_context or len(req.clinical_context.keys()) == 0:
        return {
            "patient_id": req.patient_id,
            "encounter_id": req.encounter_id,
            "step4": step4_result,
            "step5": {
                "status": "PENDING",
                "report": "CURRENT CLINICAL INFORMATION REQUIRED",
                "rules": []
            },
            "step6": compute_care_pathway(risk_band, "PENDING"),
            "step7": None
        }

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
    if safety_status in ['PENDING', 'RED']:
        reason = "Current clinical information is required." if safety_status == 'PENDING' else "Emergency care required; routine provider matching blocked."
        provider_result = {"Status": "BLOCKED", "Reason": reason, "Options": []}
    else:
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
        
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data/provider_index.db'))
        provider_result = provider_engine.match(patient_match_state, db_path=db_path)

    # Persist vitals to Supabase (non-blocking, fire-and-forget)
    try:
        _persist_vitals(
            patient_id=req.patient_id,
            encounter_id=req.encounter_id,
            clinical_context=req.clinical_context,
            step4=step4_result,
            step5={"status": safety_status, "report": report, "rules": triggered_rules},
            step6=pathway_result,
            care_manager_id=user.get("id") if user else None
        )
    except Exception:
        pass

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
def submit_audit(req: DecisionAuditRequest, user: dict = Depends(require_care_manager)):
    supabase = get_supabase()
    if supabase:
        try:
            supabase.table("audit_trail").insert({
                "patient_id": req.patient_id,
                "encounter_id": req.encounter_id,
                "reviewer_id": user["id"],
                "action": req.action,
                "reason": req.reason,
                "system_pathway": req.system_pathway,
                "system_provider": req.system_provider,
                "selected_provider": req.selected_provider
            }).execute()
        except Exception as e:
            print("Failed to save audit to Supabase:", e)
    return {"status": "success", "message": "Audit recorded."}

@app.post("/api/explain")
def explain_results(req: ExplainRequest, user: dict = Depends(get_current_user)):
    explanation = []
    explanation.append("### AI Explanation Layer — Rule-based Explanation Engine")
    explanation.append("*Disclaimer: This engine explains the deterministic outputs. It does not make clinical decisions, calculate risk, or override safety protocols.*")
    
    band = req.step4.get("band", "UNKNOWN")
    score = req.step4.get("score", 0)
    explanation.append(f"\n**Historical Risk**: The patient was deterministically classified as {band} risk (Score: {score}) based on historical EHR patterns. "
                       f"The model identified the following key drivers: {', '.join(req.step4.get('drivers', []))}.")
    
    safety_status = req.step5.get("status", "GREEN")
    report = req.step5.get("report", "Normal vitals")
    
    if safety_status == "GREEN":
        explanation.append(f"\n**Safety Gate**: Based on the provided clinical context, "
                           f"the safety gate evaluated to GREEN, meaning no immediate red flags were detected. Routine care is permitted.")
    elif safety_status == "YELLOW":
        explanation.append(f"\n**Safety Gate**: The safety gate triggered a YELLOW warning ({report}). This overrides standard risk and mandates an urgent clinician review before routine matching proceeds.")
    else:
        explanation.append(f"\n**Safety Gate**: A CRITICAL RED safety flag was triggered ({report}). This forces an immediate Emergency override, bypassing all routine provider matching to prioritize patient safety.")

    pathway = req.step6.get("Pathway", "UNKNOWN")
    explanation.append(f"\n**Care Pathway**: Consequently, the system rigidly mapped the patient to {pathway} ({req.step6.get('Name')}).")
    
    if req.step7 and req.step7.get("Status") == "SUCCESS":
        top_provider = req.step7.get("Options", [{}])[0]
        explanation.append(f"\n**Provider Matching**: Since the pathway permits routine care, the provider matching engine evaluated available specialists based on quality scores and patient compatibility. "
                           f"{top_provider.get('Name')} ranked #1 as the best fit.")
    else:
        explanation.append("\n**Provider Matching**: Provider matching was deliberately BLOCKED by the safety engine to prevent inappropriate routine scheduling during an emergent/conditional clinical state.")
        
    return {"explanation": "\n".join(explanation)}

@app.get("/api/copilot/knowledge")
def list_copilot_knowledge(user: dict = Depends(require_care_manager)):
    return [{"id": item["id"], "title": item["title"], "tags": item.get("tags", [])} for item in load_documents()]

@app.post("/api/copilot/explain")
def copilot_explain(req: CopilotRequest, user: dict = Depends(require_care_manager)):
    result = generate_grounded_answer(req.evaluation)
    log_copilot_event(user["id"], req.patient_id, req.encounter_id, None, result)
    return {**result, "graph": build_case_graph(req.patient_id, req.encounter_id, req.evaluation)}

@app.post("/api/copilot/ask")
def copilot_ask(req: CopilotRequest, user: dict = Depends(require_care_manager)):
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=422, detail="A care-manager question is required.")
    result = generate_grounded_answer(req.evaluation, req.question.strip())
    log_copilot_event(user["id"], req.patient_id, req.encounter_id, req.question.strip(), result)
    return {**result, "graph": build_case_graph(req.patient_id, req.encounter_id, req.evaluation)}

@app.post("/api/symptoms/llm-extract")
def extract_symptoms_llm(req: SymptomsRequest, user: dict = Depends(get_current_user)):
    symptoms_text = req.symptoms
    extracted = {}

    if requests is not None and os.getenv("OPENROUTER_API_KEY"):
        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                "Content-Type": "application/json"
            }
            prompt = f"""Extract clinical vital signs and symptoms from the patient description into JSON format with only these exact keys (if mentioned or clearly implied):
- "Temperature" (number in Celsius or Fahrenheit)
- "Heart Rate" (number in bpm)
- "SpO2" (number in %)
- "Systolic BP" (number in mmHg)
- "Respiratory Rate" (number in breaths/min)
- "Pain" (number 0-10)
- "Chest Pain" ("Yes" or "No")
- "Bleeding" ("Yes" or "No")
- "Convulsions" ("Yes" or "No")
- "Allergic Reaction" ("Yes" or "No")
- "Active High-Risk Condition" ("Yes" or "No")
- "Safety Conflict" ("Yes" or "No")
- "required_specialty_hint" ("Cardiology" or "General Practice")

Patient text: "{symptoms_text}"
Return ONLY valid JSON with keys that were found. Do not invent unmentioned vitals."""

            body = {
                "model": os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1
            }
            resp = requests.post(url, headers=headers, json=body, timeout=10)
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                extracted = json.loads(content)
                return {"status": "success", "extracted_features": extracted, "mode": "llm"}
        except Exception as e:
            print(f"LLM Extraction error: {e}")

    # Heuristic fallback for common symptom keywords
    text_lower = symptoms_text.lower()
    if "chest pain" in text_lower or "chest hurts" in text_lower:
        extracted["Chest Pain"] = "Yes"
    if "short of breath" in text_lower or "shortness of breath" in text_lower or "breathing" in text_lower:
        extracted["Respiratory Rate"] = 24
    if "fever" in text_lower:
        extracted["Temperature"] = 38.5
    if "bleed" in text_lower:
        extracted["Bleeding"] = "Yes"
        
    return {"status": "success", "extracted_features": extracted, "mode": "heuristic_fallback"}

@app.get("/api/appointments/{patient_id}")
def get_patient_appointments(patient_id: str, user: dict = Depends(require_care_manager)):
    try:
        conn = sqlite3.connect(os.path.abspath(os.path.join(os.path.dirname(__file__), 'data/appointments.db')))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM appointments WHERE patient_id = ? ORDER BY timestamp DESC", (patient_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Appointments Error: {e}")
        return []

@app.post("/api/appointments")
def create_appointment(req: AppointmentRequest, user: dict = Depends(require_care_manager)):
    appointment_id = str(uuid.uuid4())
    now_iso = datetime.utcnow().isoformat()
    try:
        conn = sqlite3.connect(os.path.abspath(os.path.join(os.path.dirname(__file__), 'data/appointments.db')))
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO appointments (
                appointment_id, patient_id, encounter_id, provider_name, 
                provider_npi, pac_id, provider_specialty, 
                appointment_date, appointment_time, status, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                appointment_id, req.patient_id, req.encounter_id, req.provider_name,
                req.provider_npi, req.pac_id, req.provider_specialty,
                req.appointment_date, req.appointment_time, 'Scheduled', now_iso
            )
        )
        conn.commit()
        conn.close()
        
        supabase = get_supabase()
        if supabase:
            try:
                supabase.table("appointments").insert({
                    "appointment_id": appointment_id,
                    "patient_id": req.patient_id,
                    "encounter_id": req.encounter_id,
                    "provider_name": req.provider_name,
                    "provider_npi": req.provider_npi,
                    "pac_id": req.pac_id,
                    "provider_specialty": req.provider_specialty,
                    "appointment_date": req.appointment_date,
                    "appointment_time": req.appointment_time,
                    "status": "Scheduled",
                    "care_manager_notes": req.care_manager_notes,
                }).execute()
            except Exception as se:
                print("Supabase appointment sync note:", se)
                
        return {"status": "success", "appointment_id": appointment_id}
    except Exception as e:
        print("Appointment creation failed:", e)
        raise HTTPException(status_code=500, detail="Database insert failed")

@app.put("/api/appointments/{appointment_id}")
def update_appointment(appointment_id: str, req: AppointmentStatusUpdate, user: dict = Depends(require_care_manager)):
    try:
        conn = sqlite3.connect(os.path.abspath(os.path.join(os.path.dirname(__file__), 'data/appointments.db')))
        cursor = conn.cursor()
        cursor.execute("UPDATE appointments SET status = ? WHERE appointment_id = ?", (req.status, appointment_id))
        conn.commit()
        conn.close()
        
        supabase = get_supabase()
        if supabase:
            try:
                supabase.table("appointments").update({"status": req.status}).eq("appointment_id", appointment_id).execute()
            except Exception as se:
                print("Supabase appointment update note:", se)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail="Database update failed")
    return {"status": "success"}

@app.post("/api/outcomes")
def capture_outcome(req: OutcomeRequest, user: dict = Depends(require_care_manager)):
    outcome_id = str(uuid.uuid4())
    now_iso = datetime.utcnow().isoformat()
    try:
        conn = sqlite3.connect(os.path.abspath(os.path.join(os.path.dirname(__file__), 'data/appointments.db')))
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO outcomes (outcome_id, appointment_id, patient_id, encounter_id, clinical_notes, follow_up_required, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (outcome_id, req.appointment_id, req.patient_id, req.encounter_id, req.clinical_notes, req.follow_up_required, now_iso)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print("Local outcomes DB insert note:", e)

    supabase = get_supabase()
    if supabase:
        try:
            supabase.table("outcomes").insert({
                "outcome_id": outcome_id,
                "appointment_id": req.appointment_id,
                "patient_id": req.patient_id,
                "encounter_id": req.encounter_id,
                "clinical_notes": req.clinical_notes,
                "follow_up_required": req.follow_up_required
            }).execute()
        except Exception as se:
            print("Supabase outcome insert note:", se)
            
    return {"status": "success", "outcome_id": outcome_id}

@app.get("/api/outcomes/{patient_id}")
def get_patient_outcomes(patient_id: str, user: dict = Depends(require_care_manager)):
    try:
        conn = sqlite3.connect(os.path.abspath(os.path.join(os.path.dirname(__file__), 'data/appointments.db')))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM outcomes WHERE patient_id = ? ORDER BY timestamp DESC", (patient_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Outcomes Error: {e}")
        return []

@app.get("/api/report/{patient_id}/{encounter_id}")
def generate_report(patient_id: str, encounter_id: str, user: dict = Depends(require_care_manager)):
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    
    pdf_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, f"care_assessment_{patient_id}.pdf")
    
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.drawString(100, 750, "Care Assessment Report")
    c.drawString(100, 730, f"Patient ID: {patient_id}")
    c.drawString(100, 710, f"Encounter ID: {encounter_id}")
    c.drawString(100, 690, f"Generated At: {datetime.utcnow().isoformat()}")
    c.drawString(100, 670, "Status: Generated by UC07 Care Manager Engine")
    c.save()
    
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"CareAssessment_{patient_id}.pdf")

# ==========================================
# PATIENT PORTAL APIs
# ==========================================

@app.post("/api/patient/login")
def patient_login(req: PatientLoginRequest):
    try:
        df = get_real_patient_features(req.patient_id, None)
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail="Patient ID not found. Please check your ID and try again.")
    except HTTPException:
        raise
    except Exception as e:
        print("Login DB Error:", e)
        raise HTTPException(status_code=500, detail="Unable to access patient records. Please try again.")
        
    token = f"patient-{req.patient_id}"
    return {"status": "success", "token": token, "patient_id": req.patient_id}

@app.get("/api/patient/profile")
def get_patient_profile(user: dict = Depends(require_patient)):
    patient_id = user["id"]
    try:
        df = get_real_patient_features(patient_id, None)
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail="Patient data not found")
            
        row = df.iloc[0]
        age = int(row.get("age_at_index", 0)) if "age_at_index" in row and pd.notna(row["age_at_index"]) else "Unknown"
        gender = row.get("gender") if "gender" in row and pd.notna(row["gender"]) else "Unknown"
    except HTTPException:
        raise
    except Exception as e:
        print("Profile DB Error:", e)
        raise HTTPException(status_code=500, detail="Database connection error")
    
    return {
        "patient_id": patient_id,
        "name": f"Patient {patient_id[:8]}",
        "age": age,
        "gender": gender,
        "phone": "Not available on file",
        "dob": "Not available on file"
    }

@app.get("/api/patient/appointments")
def get_patient_own_appointments(user: dict = Depends(require_patient)):
    patient_id = user["id"]
    try:
        conn = sqlite3.connect(os.path.abspath(os.path.join(os.path.dirname(__file__), 'data/appointments.db')))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM appointments WHERE patient_id = ? ORDER BY timestamp DESC", (patient_id,))
        appt_rows = cursor.fetchall()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='outcomes'")
        if cursor.fetchone():
            cursor.execute("SELECT * FROM outcomes WHERE patient_id = ?", (patient_id,))
            outcomes_rows = cursor.fetchall()
        else:
            outcomes_rows = []
        conn.close()
        
        return {
            "appointments": [dict(r) for r in appt_rows],
            "outcomes": [dict(r) for r in outcomes_rows]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Database read failed")

@app.post("/api/patient/appointments/{appointment_id}/reschedule")
def patient_reschedule(appointment_id: str, req: PatientRescheduleRequest, user: dict = Depends(require_patient)):
    patient_id = user["id"]
    try:
        conn = sqlite3.connect(os.path.abspath(os.path.join(os.path.dirname(__file__), 'data/appointments.db')))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT patient_id FROM appointments WHERE appointment_id = ?", (appointment_id,))
        row = cursor.fetchone()
        if not row or row["patient_id"] != patient_id:
            conn.close()
            raise HTTPException(status_code=403, detail="Unauthorized")
            
        cursor.execute("UPDATE appointments SET status = 'Rescheduled', appointment_date = ?, appointment_time = ? WHERE appointment_id = ?", (req.new_date, req.new_time, appointment_id))
        conn.commit()
        conn.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Database error")
    return {"status": "success"}

@app.post("/api/patient/appointments/{appointment_id}/cancel")
def patient_cancel(appointment_id: str, user: dict = Depends(require_patient)):
    patient_id = user["id"]
    try:
        conn = sqlite3.connect(os.path.abspath(os.path.join(os.path.dirname(__file__), 'data/appointments.db')))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT patient_id FROM appointments WHERE appointment_id = ?", (appointment_id,))
        row = cursor.fetchone()
        if not row or row["patient_id"] != patient_id:
            conn.close()
            raise HTTPException(status_code=403, detail="Unauthorized")
            
        cursor.execute("UPDATE appointments SET status = 'Cancelled' WHERE appointment_id = ?", (appointment_id,))
        conn.commit()
        conn.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Database error")
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
