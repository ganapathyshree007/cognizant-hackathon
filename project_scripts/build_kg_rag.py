"""Create an auditable local evidence graph and starter governed RAG index.

CMS model data, Synthea safety data, and provider-directory data deliberately
remain separate populations. No synthetic patient IDs are joined to CMS IDs.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd


def driver_rows(row: pd.Series) -> list[tuple[str, str]]:
    drivers = []
    if row.get("ed_visits_90d", 0) >= 1: drivers.append(("repeat_ed_pattern", "At least one ED-candidate event in the prior 90 days."))
    if row.get("outpatient_visits_90d", 0) == 0: drivers.append(("no_recent_outpatient_visit", "No outpatient claim events in the prior 90 days."))
    if row.get("inpatient_visits_90d", 0) >= 1: drivers.append(("recent_inpatient_use", "At least one inpatient claim event in the prior 90 days."))
    if row.get("chronic_condition_burden", 0) >= 3: drivers.append(("chronic_condition_burden", "Three or more recorded chronic-condition flags."))
    if not drivers: drivers.append(("limited_historical_signal", "No predefined utilization driver crossed the evidence threshold."))
    return drivers


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args(); root = args.project_root
    sys.path.insert(0, str(root / "model_runtime" / "python_packages"))
    import joblib
    report = json.loads((root / "model_artifacts" / "model_report.json").read_text(encoding="utf-8"))
    model = joblib.load(root / "model_artifacts" / "repeat_ed_risk_model.joblib")
    features = pd.read_csv(root / "model_training_data" / "model_features.csv")
    features = features[features["split"].isin(["train", "test"])].copy()
    probabilities = model.predict_proba(features[report["feature_columns"]])[:, 1]
    threshold = report["selected_operating_threshold"]
    features["risk_score"] = probabilities.round(6)
    features["risk_band"] = pd.cut(features["risk_score"], bins=[-1, threshold * .7, threshold, 1], labels=["LOW", "MEDIUM", "HIGH"]).astype(str)
    features["case_id"] = features["member_id"].astype(str) + "::" + features["index_date"].astype(str)
    evidence_cols = ["case_id", "member_id", "index_date", "risk_score", "risk_band", "repeat_ed_within_90d", "split", "ed_visits_90d", "outpatient_visits_90d", "inpatient_visits_90d", "chronic_condition_burden"]
    kg_dir = root / "kg_rag"; kg_dir.mkdir(parents=True, exist_ok=True)
    features[evidence_cols].to_csv(kg_dir / "cms_case_evidence.csv", index=False)

    db_path = kg_dir / "evidence_graph.sqlite"
    if db_path.exists(): db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.executescript("""
      CREATE TABLE nodes (node_type TEXT NOT NULL, node_id TEXT NOT NULL, attributes_json TEXT NOT NULL, PRIMARY KEY (node_type, node_id));
      CREATE TABLE edges (source_type TEXT NOT NULL, source_id TEXT NOT NULL, relation TEXT NOT NULL, target_type TEXT NOT NULL, target_id TEXT NOT NULL, evidence_text TEXT);
      CREATE INDEX ix_edges_source ON edges(source_type, source_id);
      CREATE INDEX ix_edges_target ON edges(target_type, target_id);
    """)
    node_rows, edge_rows = [], []
    for _, row in features.iterrows():
        member_id, case_id = str(row.member_id), row.case_id
        node_rows.append(("cms_member", member_id, json.dumps({"population": "CMS_DE_SYNPuf"})))
        node_rows.append(("cms_case", case_id, json.dumps({"index_date": str(row.index_date), "risk_score": float(row.risk_score), "risk_band": row.risk_band})))
        edge_rows.append(("cms_member", member_id, "HAS_MODEL_CASE", "cms_case", case_id, "Claims-derived index case."))
        for code, text in driver_rows(row):
            driver_id = f"{case_id}::{code}"
            node_rows.append(("utilization_driver", driver_id, json.dumps({"driver": code})))
            edge_rows.append(("cms_case", case_id, "HAS_DRIVER", "utilization_driver", driver_id, text))
    safety = pd.read_csv(root / "safety_engine_output" / "synthea_safety_cases.csv")
    for _, row in safety.iterrows():
        node_rows.append(("synthea_member", str(row.member_id), json.dumps({"population": "Synthea"})))
        node_rows.append(("synthea_safety_case", str(row.encounter_id), json.dumps({"status": row.safety_status, "index_datetime": str(row.index_datetime)})))
        edge_rows.append(("synthea_member", str(row.member_id), "HAS_SAFETY_CASE", "synthea_safety_case", str(row.encounter_id), str(row.safety_drivers)))
    conn.executemany("INSERT OR REPLACE INTO nodes VALUES (?, ?, ?)", node_rows)
    conn.executemany("INSERT INTO edges VALUES (?, ?, ?, ?, ?, ?)", edge_rows)
    conn.commit()
    counts = {"nodes": conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0], "edges": conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]}
    conn.close()

    kb = kg_dir / "knowledge_base"; kb.mkdir(exist_ok=True)
    (kb / "system_governance.md").write_text("""# Avoidable ED Navigator: system governance evidence\n\n- The risk score estimates repeat ED-candidate utilization within 90 days; it does not determine avoidability, diagnosis, or acuity.\n- Utilization features are calculated using events strictly before the index date.\n- A possible emergency or missing current clinical data must stop lower-acuity navigation and require human clinical review.\n- Provider ranking is decision support after pathway selection. Missing quality or telehealth information is treated as unknown, not negative evidence.\n- Synthea and CMS patient populations are separate and must never be joined by patient identifier.\n""", encoding="utf-8")
    (kb / "approved_guidance_placeholder.md").write_text("""# Add approved guidance here\n\nAdd only organization-approved care-navigation protocols, escalation policies, referral criteria, and provider-network policies. Each document should include owner, approval date, and review date. The starter RAG layer must not use unapproved clinical content.\n""", encoding="utf-8")
    documents = []
    for path in kb.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        documents.append({"document_id": path.stem, "path": str(path), "text": text, "approved_for_retrieval": path.name != "approved_guidance_placeholder.md"})
    (kg_dir / "rag_document_index.json").write_text(json.dumps(documents, indent=2), encoding="utf-8")
    manifest = {"graph_boundary": "CMS model graph and Synthea safety graph are separate; provider catalog remains a directory queried after pathway selection.", "cms_cases": len(features), "synthea_safety_cases": len(safety), "graph": counts, "rag_documents": len(documents), "retrieval_enabled_documents": sum(d["approved_for_retrieval"] for d in documents)}
    (kg_dir / "kg_rag_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
