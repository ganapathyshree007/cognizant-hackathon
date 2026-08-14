"""Avoidable ED Navigator API: decision support, never autonomous triage."""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

PROJECT_ROOT = Path(os.environ.get("NAVIGATOR_PROJECT_ROOT", r"C:\COGNIZANT HACKATHON"))
import sys
sys.path.insert(0, str(PROJECT_ROOT / "model_runtime" / "python_packages"))

from fastapi import FastAPI, HTTPException, Query

KG_DB = PROJECT_ROOT / "kg_rag" / "evidence_graph.sqlite"
PROVIDER_DB = PROJECT_ROOT / "provider_catalog" / "provider_catalog.sqlite"
SAFETY_FILE = PROJECT_ROOT / "safety_engine_output" / "synthea_safety_cases.csv"

PATHWAYS = {
    "PRIMARY_CARE": ["GENERAL PRACTICE", "FAMILY PRACTICE", "INTERNAL MEDICINE", "GERIATRIC MEDICINE"],
    "TELEHEALTH": ["GENERAL PRACTICE", "FAMILY PRACTICE", "INTERNAL MEDICINE"],
    "CARE_MANAGEMENT": ["CLINICAL SOCIAL WORKER", "NURSE PRACTITIONER", "GENERAL PRACTICE", "INTERNAL MEDICINE"],
    "URGENT_CARE": ["EMERGENCY MEDICINE", "FAMILY PRACTICE", "GENERAL PRACTICE", "INTERNAL MEDICINE"],
}

def kg_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(KG_DB); conn.row_factory = sqlite3.Row; return conn

def provider_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(PROVIDER_DB); conn.row_factory = sqlite3.Row; return conn

def provider_search(pathway: str, state: str | None, require_telehealth: bool, limit: int) -> list[dict]:
    specialties = PATHWAYS[pathway]
    where = ["(" + " OR ".join(["UPPER(primary_specialty) LIKE ?" for _ in specialties]) + ")"]
    params: list[object] = [f"%{s}%" for s in specialties]
    if state:
        where.append("UPPER(state)=?"); params.append(state.upper())
    if require_telehealth:
        where.append("telehealth_available='YES'")
    sql = f"""SELECT NPI, first_name, last_name, Cred, primary_specialty, telehealth_available, city, state, zip, phone,
                     mips_score, quality_data_available, affiliated_facility_count, affiliated_facility_types
              FROM providers WHERE {' AND '.join(where)}
              ORDER BY CASE WHEN mips_score IS NULL THEN 1 ELSE 0 END, mips_score DESC, affiliated_facility_count DESC LIMIT ?"""
    params.append(limit)
    with provider_connection() as conn:
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    for row in rows:
        row["ranking_notice"] = "Directory option only; care manager must verify network, availability, accessibility, and clinical fit."
    return rows

@asynccontextmanager
async def lifespan(app: FastAPI):
    missing = [str(p) for p in (KG_DB, PROVIDER_DB, SAFETY_FILE) if not p.exists()]
    if missing: raise RuntimeError(f"Missing required project artifacts: {missing}")
    yield

app = FastAPI(title="Avoidable ED Utilization Navigator", version="0.1.0", lifespan=lifespan)

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "avoidable-ed-navigator", "clinical_notice": "Decision support only; never autonomous triage."}

@app.get("/v1/cms/cases/{case_id}/review")
def cms_case_review(case_id: str) -> dict:
    with kg_connection() as conn:
        row = conn.execute("SELECT attributes_json FROM nodes WHERE node_type='cms_case' AND node_id=?", (case_id,)).fetchone()
        drivers = conn.execute("SELECT target_id, evidence_text FROM edges WHERE source_type='cms_case' AND source_id=? AND relation='HAS_DRIVER'", (case_id,)).fetchall()
    if not row:
        raise HTTPException(404, detail={"status": "DATA_NOT_FOUND", "message": "CMS model case was not found. Verify the case ID and authorized data source."})
    return {
        "case_id": case_id, "risk": json.loads(row["attributes_json"]),
        "drivers": [{"driver_id": d["target_id"].rsplit("::", 1)[-1], "evidence": d["evidence_text"]} for d in drivers],
        "safety_status": "INSUFFICIENT_CURRENT_CLINICAL_DATA",
        "navigation_eligible": False,
        "recommended_action": "Obtain current clinical assessment and human care-manager/clinician review before any pathway recommendation.",
        "notice": "CMS and Synthea populations are separate. This endpoint does not infer a Synthea safety result for a CMS case."
    }

@app.get("/v1/synthea/safety-cases/{encounter_id}")
def synthea_safety_review(encounter_id: str) -> dict:
    # Read by scan is deliberate for the small demo safety file; no cross-population join occurs.
    import pandas as pd
    rows = pd.read_csv(SAFETY_FILE, dtype=str)
    result = rows.loc[rows["encounter_id"].eq(encounter_id)]
    if result.empty:
        raise HTTPException(404, detail={"status": "DATA_NOT_FOUND", "message": "Synthea safety case not found."})
    row = result.iloc[0].where(result.iloc[0].notna(), None).to_dict()
    row["navigation_eligible"] = False
    row["notice"] = "Prototype safety evidence only. Human clinical review is required; no lower-acuity clearance is automated."
    return row

@app.get("/v1/providers/search")
def search_providers(
    pathway: Literal["PRIMARY_CARE", "TELEHEALTH", "CARE_MANAGEMENT", "URGENT_CARE"],
    state: str | None = Query(default=None, min_length=2, max_length=2),
    require_telehealth: bool = False,
    limit: int = Query(default=5, ge=1, le=20),
) -> dict:
    providers = provider_search(pathway, state, require_telehealth, limit)
    return {"pathway": pathway, "state": state, "require_telehealth": require_telehealth, "providers": providers,
            "notice": "Provider search does not establish clinical appropriateness, coverage, or appointment availability."}
