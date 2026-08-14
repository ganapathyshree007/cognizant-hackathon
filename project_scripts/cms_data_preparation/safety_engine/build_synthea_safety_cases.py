"""Create auditable Synthea safety-review cases using configurable conservative rules.

This demonstration code must not be used for clinical triage without formal
clinical validation, governance approval, and local protocol review.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthea-dir", type=Path, required=True)
    parser.add_argument("--rules", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rules = json.loads(args.rules.read_text(encoding="utf-8"))

    encounters = pd.read_csv(args.synthea_dir / "encounters.csv", dtype="string", keep_default_na=False)
    observations = pd.read_csv(args.synthea_dir / "observations.csv", dtype="string", keep_default_na=False)
    encounters["START"] = pd.to_datetime(encounters["START"], errors="coerce")
    observations["DATE"] = pd.to_datetime(observations["DATE"], errors="coerce")
    emergency = encounters.loc[encounters["ENCOUNTERCLASS"].str.lower().eq("emergency")].copy()
    emergency = emergency.rename(columns={"Id": "encounter_id", "PATIENT": "member_id", "START": "index_datetime", "REASONDESCRIPTION": "reason_description"})

    terms = "|".join(rules["red_flag_reason_terms"])
    emergency["reason_red_flag"] = emergency["reason_description"].str.contains(terms, case=False, na=False, regex=True)
    vital_rows = observations.loc[observations["DESCRIPTION"].isin(rules["vital_rules"].keys()) & observations["ENCOUNTER"].notna()].copy()
    vital_rows["value_numeric"] = pd.to_numeric(vital_rows["VALUE"], errors="coerce")
    vital_rows["vital_abnormal"] = False
    for description, limits in rules["vital_rules"].items():
        mask = vital_rows["DESCRIPTION"].eq(description)
        vital_rows.loc[mask, "vital_abnormal"] = ((vital_rows.loc[mask, "value_numeric"] < limits["low"]) | (vital_rows.loc[mask, "value_numeric"] > limits["high"]))

    vital_summary = vital_rows.groupby("ENCOUNTER").agg(
        vital_measure_count=("DESCRIPTION", "nunique"),
        abnormal_vital_count=("vital_abnormal", "sum"),
        abnormal_vital_names=("DESCRIPTION", lambda x: "|".join(sorted(x[vital_rows.loc[x.index, "vital_abnormal"]].unique())) if vital_rows.loc[x.index, "vital_abnormal"].any() else ""),
    )
    vital_summary = vital_summary.reset_index().rename(columns={"ENCOUNTER": "encounter_id"})
    cases = emergency.merge(vital_summary, on="encounter_id", how="left")
    cases[["vital_measure_count", "abnormal_vital_count"]] = cases[["vital_measure_count", "abnormal_vital_count"]].fillna(0).astype(int)
    cases["abnormal_vital_names"] = cases["abnormal_vital_names"].fillna("")
    cases["safety_status"] = "CLINICAL_REVIEW_REQUIRED"
    cases.loc[cases["vital_measure_count"].eq(0), "safety_status"] = "INSUFFICIENT_CLINICAL_DATA"
    cases.loc[cases["reason_red_flag"] | cases["abnormal_vital_count"].gt(0), "safety_status"] = "POSSIBLE_EMERGENCY"
    cases["safety_drivers"] = cases.apply(lambda r: "|".join(filter(None, ["red_flag_reason" if r.reason_red_flag else "", f"abnormal_vitals:{r.abnormal_vital_names}" if r.abnormal_vital_count else "", "no_linked_vitals" if r.vital_measure_count == 0 else ""])), axis=1)
    output_columns = ["member_id", "encounter_id", "index_datetime", "DESCRIPTION", "reason_description", "reason_red_flag", "vital_measure_count", "abnormal_vital_count", "abnormal_vital_names", "safety_status", "safety_drivers"]
    cases[output_columns].to_csv(args.output_dir / "synthea_safety_cases.csv", index=False)
    report = {"rules_version": rules["version"], "case_count": len(cases), "status_counts": cases["safety_status"].value_counts().to_dict(), "clinical_notice": "Prototype-only. These rules require clinician validation and must never autonomously redirect emergency care."}
    (args.output_dir / "safety_case_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
