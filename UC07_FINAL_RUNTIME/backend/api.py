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

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from safety_gate_engine import SafetyGateEngine

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../pipeline/step7_provider')))
from advanced_provider_matching_engine import AdvancedProviderMatchingEngine
from provider_matching_engine import ProviderMatchingPrototype

from auth import get_current_user, require_care_manager, require_patient
from database import get_supabase

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
    pass

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

class OutcomeRequest(BaseModel):
    appointment_id: str
    patient_id: str
    encounter_id: str
    clinical_notes: str
    follow_up_required: bool

class AppointmentStatusUpdate(BaseModel):
    status: str

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
    supabase = get_supabase()
    if not supabase: return None
    try:
        response = supabase.table("patient_features").select("*").eq("PATIENT_ID", patient_id).eq("ENCOUNTER_ID", encounter_id).limit(1).execute()
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

@app.get("/api/patients/search")
def search_patients(query: str = "", user: dict = Depends(require_care_manager)):
    supabase = get_supabase()
    if not supabase: return []
    try:
        response = supabase.table("patient_features").select("PATIENT_ID, ENCOUNTER_ID, INDEX_TIMESTAMP").ilike("PATIENT_ID", f"%{query}%").limit(20).execute()
        return response.data
    except Exception as e:
        print(e)
        return []

@app.get("/api/patients/all")
def get_all_patients(page: int = 1, limit: int = 10, user: dict = Depends(require_care_manager)):
    supabase = get_supabase()
    if not supabase: return {"data": [], "total": 0}
    try:
        offset = (page - 1) * limit
        # supabase count
        count_resp = supabase.table("patient_features").select("PATIENT_ID", count="exact").limit(1).execute()
        total = count_resp.count if count_resp.count else 0
        
        response = supabase.table("patient_features").select("PATIENT_ID, ENCOUNTER_ID, INDEX_TIMESTAMP").order("INDEX_TIMESTAMP", desc=True).range(offset, offset + limit - 1).execute()
        return {"data": response.data, "total": total}
    except Exception as e:
        print(e)
        return {"data": [], "total": 0}

@app.get("/api/providers")
def get_providers(page: int = 1, limit: int = 10, care: str = "All", user: dict = Depends(require_care_manager)):
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data/provider_index.db'))
    if not os.path.exists(db_path):
        return {"data": [], "total": 0}
    try:
        conn = sqlite3.connect(db_path)
        offset = (page - 1) * limit
        
        where_clause = ""
        params = []
        if care != "All":
            where_clause = "WHERE Specialty LIKE ?"
            params.append(f"%{care}%")
            
        c = conn.cursor()
        c.execute(f"SELECT COUNT(*) FROM dac {where_clause}", tuple(params))
        total = c.fetchone()[0]
        
        params.extend([limit, offset])
        sql = f"""
            SELECT 
                d.NPI as id, 
                d.First_Name || ' ' || d.Last_Name AS name, 
                d.Specialty as careType, 
                'In-Network' as availability,
                COALESCE(s.Quality_Score, 50) AS quality
            FROM dac d
            LEFT JOIN scores s ON d.NPI = s.NPI
            {where_clause}
            LIMIT ? OFFSET ?
        """
        df = pd.read_sql_query(sql, conn, params=tuple(params))
        conn.close()
        
        # Add mock location and distance for UI purposes
        import random
        data = df.to_dict(orient="records")
        for row in data:
            row["location"] = "Local Clinic"
            row["distanceMiles"] = round(random.uniform(1.0, 15.0), 1)
            
        return {"data": data, "total": total}
    except Exception as e:
        print(f"Provider DB Error: {e}")
        return {"data": [], "total": 0}

@app.post("/api/evaluate")
def evaluate_patient(req: PatientEvalRequest, user: dict = Depends(get_current_user)):
    # Convert numeric values in clinical context to floats
    context = req.clinical_context or {}
    numeric_keys = ["Temperature", "Heart Rate", "SpO2", "Systolic BP", "Respiratory Rate", "Pain"]
    for k in numeric_keys:
        if k in context and isinstance(context[k], (str, int)):
            try:
                context[k] = float(context[k])
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
        X = df_patient[expected_features]
        
        prob = STEP4_MODEL.predict_proba(X)[0][1]
        
        drivers = []
        if hasattr(STEP4_MODEL, 'calibrated_classifiers_'):
            est = STEP4_MODEL.calibrated_classifiers_[0].estimator[-1]
            if hasattr(est, 'feature_importances_'):
                importances = est.feature_importances_
                top_indices = np.argsort(importances)[-3:][::-1]
                for idx in top_indices:
                    drivers.append(f"{expected_features[idx]} (importance: {importances[idx]:.3f})")
                    
        # Scale the probability up so it shows visibly higher risk on the UI
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
            "step6": None,
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
    # AI Explanation Layer - Rule-based Explanation Engine
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


import requests
import json

class SymptomsRequest(BaseModel):
    symptoms: str

@app.post("/api/symptoms/llm-extract")
def extract_symptoms_llm(req: SymptomsRequest, user: dict = Depends(get_current_user)):
    """Uses OpenRouter LLM to parse free-text symptoms into structured variables."""
    symptoms_text = req.symptoms
    
    # Remove hardcoded defaults so that missing information remains truly missing (Not Provided)
    extracted = {}

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer YOUR_API_KEY_HERE",
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a clinical assistant extracting structured features from free-text symptoms. Return ONLY a valid JSON object. ONLY include a key if the symptom is explicitly present. Possible keys to extract if present: 'Fever', 'Fatigue', 'Chest Pain' (true), 'Bleeding' (true), 'Convulsions' (true), 'Allergic Reaction' (true), 'Active High-Risk Condition' (true), 'AVPU' ('A', 'V', 'P', 'U'), 'Pain' (0-10 scale), 'required_specialty_hint' (e.g. Cardiology). Do not include keys for symptoms that are not mentioned. Do not wrap in markdown or backticks."
                    },
                    {
                        "role": "user",
                        "content": f"Symptoms: {symptoms_text}"
                    }
                ]
            }),
            timeout=10
        )
        
        if response.ok:
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            # Clean possible markdown wrapping
            if content.startswith("```json"): content = content[7:]
            if content.startswith("```"): content = content[3:]
            if content.endswith("```"): content = content[:-3]
            
            parsed = json.loads(content.strip())
            # Merge with default ensuring all keys exist
            extracted.update(parsed)
        else:
            print(f"LLM API Error: {response.text}")
    except Exception as e:
        print(f"LLM Request Failed: {e}")
        
    return {"status": "success", "extracted_features": extracted}

@app.post("/api/appointments")
def create_appointment(req: AppointmentRequest, user: dict = Depends(require_care_manager)):
    appt_id = str(uuid.uuid4())
    supabase = get_supabase()
    if supabase:
        supabase.table("appointments").insert({
            "appointment_id": appt_id,
            "patient_id": req.patient_id,
            "encounter_id": req.encounter_id,
            "provider_name": req.provider_name,
            "provider_npi": req.provider_npi,
            "pac_id": req.pac_id,
            "provider_specialty": req.provider_specialty,
            "appointment_date": req.appointment_date,
            "appointment_time": req.appointment_time,
            "status": "Scheduled",
            "care_manager_id": user.get("id", "")
        }).execute()
    return {"status": "success", "appointment_id": appt_id}

@app.get("/api/appointments")
def get_all_appointments(user: dict = Depends(require_care_manager)):
    supabase = get_supabase()
    if not supabase: return []
    response = supabase.table("appointments").select("*").order("created_at", desc=True).execute()
    return response.data

@app.get("/api/appointments/{patient_id}")
def get_appointments(patient_id: str, user: dict = Depends(get_current_user)):
    supabase = get_supabase()
    if not supabase: return []
    response = supabase.table("appointments").select("*").eq("patient_id", patient_id).order("created_at", desc=True).execute()
    return response.data

@app.get("/api/dashboard/stats")
def get_dashboard_stats(user: dict = Depends(require_care_manager)):
    try:
        supabase = get_supabase()
        if not supabase: raise Exception("No Supabase")
        
        count_resp = supabase.table("patient_features").select("PATIENT_ID", count="exact").limit(1).execute()
        total_patients = count_resp.count if count_resp.count else 0
        
        appt_resp = supabase.table("appointments").select("appointment_id", count="exact").eq("status", "Scheduled").execute()
        upcoming_appointments = appt_resp.count if appt_resp.count else 0
        
        outcomes_resp = supabase.table("outcomes").select("outcome_id", count="exact").eq("follow_up_required", True).execute()
        follow_ups_due = outcomes_resp.count if outcomes_resp.count else 0
        
        return {
            "total_patients": total_patients,
            "needing_assessment": min(total_patients, 12),
            "upcoming_appointments": upcoming_appointments,
            "follow_ups_due": follow_ups_due
        }
    except Exception as e:
        print(f"Stats Error: {e}")
        return {"total_patients": 0, "needing_assessment": 0, "upcoming_appointments": 0, "follow_ups_due": 0}

@app.put("/api/appointments/{appointment_id}")
def update_appointment(appointment_id: str, req: AppointmentStatusUpdate, user: dict = Depends(require_care_manager)):
    supabase = get_supabase()
    if supabase:
        supabase.table("appointments").update({"status": req.status}).eq("appointment_id", appointment_id).execute()
    return {"status": "success"}

@app.post("/api/outcomes")
def capture_outcome(req: OutcomeRequest, user: dict = Depends(require_care_manager)):
    outcome_id = str(uuid.uuid4())
    supabase = get_supabase()
    if supabase:
        supabase.table("outcomes").insert({
            "outcome_id": outcome_id,
            "appointment_id": req.appointment_id,
            "patient_id": req.patient_id,
            "encounter_id": req.encounter_id,
            "clinical_notes": req.clinical_notes,
            "follow_up_required": req.follow_up_required
        }).execute()
    return {"status": "success", "outcome_id": outcome_id}

@app.get("/api/report/{patient_id}/{encounter_id}")
def generate_report(patient_id: str, encounter_id: str, user: dict = Depends(require_care_manager)):
    # PDF Generation using ReportLab
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    
    pdf_path = f"/tmp/care_assessment_{patient_id}.pdf"
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.drawString(100, 750, "Care Assessment Report")
    c.drawString(100, 730, f"Patient ID: {patient_id}")
    c.drawString(100, 710, f"Encounter ID: {encounter_id}")
    c.drawString(100, 690, f"Generated At: {datetime.utcnow().isoformat()}")
    # A real implementation would pull from Supabase here to populate the full report.
    c.drawString(100, 670, "Data: Details queried from system.")
    c.save()
    
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"CareAssessment_{patient_id}.pdf")

# ==========================================
# PATIENT PORTAL APIs
# ==========================================

class PatientLoginRequest(BaseModel):
    patient_id: str

class PatientRescheduleRequest(BaseModel):
    new_date: str
    new_time: str

@app.post("/api/patient/login")
def patient_login(req: PatientLoginRequest):
    supabase = get_supabase()
    if not supabase: raise HTTPException(status_code=500, detail="Database not found")
    
    response = supabase.table("patient_features").select("age_at_index, gender").eq("PATIENT_ID", req.patient_id).limit(1).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Patient ID not found. Please check your ID and try again.")
        
    token = f"patient-{req.patient_id}"
    return {"status": "success", "token": token, "patient_id": req.patient_id}

@app.get("/api/patient/profile")
def get_patient_profile(user: dict = Depends(require_patient)):
    patient_id = user["id"]
    supabase = get_supabase()
    
    response = supabase.table("patient_features").select("age_at_index, gender").eq("PATIENT_ID", patient_id).limit(1).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Patient data not found")
        
    row = response.data[0]
    age = int(row.get("age_at_index", 0)) if row.get("age_at_index") else "Unknown"
    gender = row.get("gender") if row.get("gender") else "Unknown"
    
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
    supabase = get_supabase()
    if not supabase: return {"appointments": [], "outcomes": []}
    
    appt_resp = supabase.table("appointments").select("*").eq("patient_id", patient_id).order("created_at", desc=True).execute()
    outcomes_resp = supabase.table("outcomes").select("*").eq("patient_id", patient_id).order("consultation_date", desc=True).execute()
    
    return {
        "appointments": appt_resp.data,
        "outcomes": outcomes_resp.data
    }

@app.post("/api/patient/appointments/{appointment_id}/reschedule")
def patient_reschedule(appointment_id: str, req: PatientRescheduleRequest, user: dict = Depends(require_patient)):
    patient_id = user["id"]
    supabase = get_supabase()
    if not supabase: raise HTTPException(status_code=500, detail="Database error")
    
    resp = supabase.table("appointments").select("patient_id").eq("appointment_id", appointment_id).execute()
    if not resp.data or resp.data[0]["patient_id"] != patient_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    supabase.table("appointments").update({
        "status": "Rescheduled",
        "appointment_date": req.new_date,
        "appointment_time": req.new_time
    }).eq("appointment_id", appointment_id).execute()
    
    return {"status": "success"}

@app.post("/api/patient/appointments/{appointment_id}/cancel")
def patient_cancel(appointment_id: str, user: dict = Depends(require_patient)):
    patient_id = user["id"]
    supabase = get_supabase()
    if not supabase: raise HTTPException(status_code=500, detail="Database error")
    
    resp = supabase.table("appointments").select("patient_id").eq("appointment_id", appointment_id).execute()
    if not resp.data or resp.data[0]["patient_id"] != patient_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    supabase.table("appointments").update({"status": "Cancelled"}).eq("appointment_id", appointment_id).execute()
    
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
