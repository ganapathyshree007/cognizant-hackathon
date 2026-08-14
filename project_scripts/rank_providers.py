"""Rank CMS directory providers after a pathway has been selected by human review."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


PATHWAY_SPECIALTIES = {
    "PRIMARY_CARE": ["GENERAL PRACTICE", "FAMILY PRACTICE", "INTERNAL MEDICINE", "GERIATRIC MEDICINE"],
    "TELEHEALTH": ["GENERAL PRACTICE", "FAMILY PRACTICE", "INTERNAL MEDICINE"],
    "CARE_MANAGEMENT": ["CLINICAL SOCIAL WORKER", "NURSE PRACTITIONER", "GENERAL PRACTICE", "INTERNAL MEDICINE"],
    "URGENT_CARE": ["EMERGENCY MEDICINE", "FAMILY PRACTICE", "GENERAL PRACTICE", "INTERNAL MEDICINE"],
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--pathway", choices=PATHWAY_SPECIALTIES, required=True)
    parser.add_argument("--state", help="Two-letter state/territory code, e.g. PR")
    parser.add_argument("--require-telehealth", action="store_true")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    catalog = pd.read_csv(args.catalog, dtype="string", keep_default_na=False)
    specialties = PATHWAY_SPECIALTIES[args.pathway]
    result = catalog.copy()
    result["specialty_match"] = result["primary_specialty"].fillna("").str.upper().apply(lambda s: any(x in s for x in specialties))
    if args.state:
        result = result[result["state"].str.upper().eq(args.state.upper())]
    if args.require_telehealth:
        result = result[result["telehealth_available"].eq("YES")]
    # Prefer, but do not discard, specialty matches. If none exist, the user must broaden the pathway manually.
    result = result[result["specialty_match"]]
    result["mips_score"] = pd.to_numeric(result["mips_score"], errors="coerce")
    result["affiliated_facility_count"] = pd.to_numeric(result["affiliated_facility_count"], errors="coerce").fillna(0)
    neutral_quality = result["mips_score"].median() if result["mips_score"].notna().any() else 50.0
    result["quality_component"] = result["mips_score"].fillna(neutral_quality).clip(0, 100) * 0.15
    result["ranking_score"] = 40 + (25 if args.state else 0) + (20 if args.require_telehealth else 0) + result["quality_component"] + result["affiliated_facility_count"].gt(0).astype(int) * 2
    columns = ["NPI", "first_name", "last_name", "Cred", "primary_specialty", "secondary_specialties", "telehealth_available", "city", "state", "zip", "phone", "facility_name", "mips_score", "quality_data_available", "affiliated_facility_count", "affiliated_facility_types", "ranking_score"]
    result = result.sort_values(["ranking_score", "mips_score"], ascending=False).head(args.top_n)[columns]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(f"Returned {len(result)} providers to {args.output}")


if __name__ == "__main__":
    main()
