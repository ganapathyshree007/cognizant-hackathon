"""Create curated, Power BI-ready reporting tables for the UC07 demo.

The source clinical/synthetic populations remain separate by design.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
import pandas as pd

ROOT = Path(r"C:\COGNIZANT HACKATHON")
OUT = ROOT / "powerbi_dashboard" / "data"
OUT.mkdir(parents=True, exist_ok=True)


def write(frame: pd.DataFrame, name: str) -> None:
    frame.to_csv(OUT / name, index=False)
    print(f"{name}: {len(frame):,} rows")


# CMS proxy-risk population: model features and outcomes, not clinical safety data.
cases = pd.read_csv(ROOT / "care_management" / "pathway_recommendations.csv")
cases["index_date"] = pd.to_datetime(cases["index_date"], errors="coerce")
cases["risk_score_pct"] = (cases["risk_score"] * 100).round(1)
cases["repeat_ed_90d_flag"] = cases["repeat_ed_within_90d"].fillna(0).astype(int)
write(cases, "Fact_CMS_Cases.csv")

# Separate encounter-date table enables a proper shared date dimension in Power BI.
min_date = cases["index_date"].min()
max_date = cases["index_date"].max()
dates = pd.DataFrame({"Date": pd.date_range(min_date, max_date, freq="D")})
dates["Year"] = dates["Date"].dt.year
dates["Quarter"] = "Q" + dates["Date"].dt.quarter.astype(str)
dates["Month Number"] = dates["Date"].dt.month
dates["Month"] = dates["Date"].dt.strftime("%b")
dates["Year Month"] = dates["Date"].dt.strftime("%Y-%m")
write(dates, "Dim_Date.csv")

# Evidence drivers retained as a case-level long table for detail drill-through.
conn = sqlite3.connect(ROOT / "kg_rag" / "evidence_graph.sqlite")
nodes = pd.read_sql_query("SELECT * FROM nodes", conn)
edges = pd.read_sql_query("SELECT * FROM edges", conn)
conn.close()
print("Evidence graph schemas:", list(nodes.columns), list(edges.columns))
case_edges = edges[edges.astype(str).apply(lambda c: c.str.contains("::", regex=False)).any(axis=1)].copy()
write(case_edges, "Fact_Evidence_Links.csv")
write(nodes, "Dim_Evidence_Nodes.csv")

# Synthea safety cases are intentionally a separate population; never join to CMS members.
safety = pd.read_csv(ROOT / "safety_engine_output" / "synthea_safety_cases.csv")
safety["index_datetime"] = pd.to_datetime(safety["index_datetime"], errors="coerce")
safety["safety_date"] = safety["index_datetime"].dt.date
write(safety, "Fact_Synthea_Safety.csv")

# Small demo provider table keeps Power BI responsive. API is the authoritative full directory.
providers = pd.read_csv(ROOT / "provider_catalog" / "sample_primary_care_rankings_pr.csv")
providers["provider_name"] = (providers["first_name"].fillna("") + " " + providers["last_name"].fillna("")).str.strip()
providers["pathway"] = "PRIMARY_CARE"
write(providers, "Dim_Provider_Demo.csv")

# Operational state is read only: rows may include local test/demo events.
conn = sqlite3.connect(ROOT / "backend" / "backend_state.sqlite")
for table, file_name in [("interventions", "Fact_Interventions.csv"), ("outcomes", "Fact_Outcomes.csv"), ("audit_events", "Fact_Audit_Events.csv")]:
    frame = pd.read_sql_query(f"SELECT * FROM {table}", conn)
    write(frame, file_name)
conn.close()

manifest = {
    "purpose": "Power BI demo reporting package for UC07",
    "important_separation": "Fact_CMS_Cases is CMS proxy-risk data; Fact_Synthea_Safety is synthetic safety validation data. They must not be joined by member_id.",
    "authoritative_provider_source": "Use the protected backend provider-search API for live provider retrieval; Dim_Provider_Demo is only a compact Power BI demo table.",
}
(OUT / "README.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
