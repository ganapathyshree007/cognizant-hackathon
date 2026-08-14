"""Build a lean provider catalog and transparent ranking function from CMS sources.

All ranks are decision-support only. Quality/telehealth missingness is retained
as unknown, never interpreted as poor quality or unavailable care.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def clean_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame.columns = [c.strip() for c in frame.columns]
    for c in frame.columns:
        frame[c] = frame[c].astype("string").str.strip().replace({"": pd.NA, "nan": pd.NA})
    return frame


def npi(frame: pd.DataFrame) -> pd.DataFrame:
    frame["NPI"] = frame["NPI"].astype("string").str.replace(r"\.0$", "", regex=True).str.replace(r"\D", "", regex=True).str.zfill(10)
    return frame[frame["NPI"].str.len().eq(10)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(); args.output_dir.mkdir(parents=True, exist_ok=True)

    provider = npi(clean_columns(pd.read_csv(args.sources_dir / "DAC_NationalDownloadableFile.csv", dtype="string", keep_default_na=False)))
    provider = provider.rename(columns={
        "Provider Last Name": "last_name", "Provider First Name": "first_name", "pri_spec": "primary_specialty",
        "sec_spec_all": "secondary_specialties", "City/Town": "city", "State": "state", "ZIP Code": "zip",
        "Telephone Number": "phone", "Telehlth": "telehealth_indicator", "Facility Name": "facility_name"
    })
    provider["telehealth_available"] = provider["telehealth_indicator"].str.upper().map({"Y": "YES", "N": "NO"}).fillna("UNKNOWN")
    keep = ["NPI", "first_name", "last_name", "Cred", "primary_specialty", "secondary_specialties", "telehealth_available", "city", "state", "zip", "phone", "facility_name", "ind_assgn", "grp_assgn"]
    provider = provider[[c for c in keep if c in provider]].drop_duplicates("NPI")

    score = npi(clean_columns(pd.read_csv(args.sources_dir / "ec_score_file.csv", dtype="string", keep_default_na=False)))
    score["final_MIPS_score"] = pd.to_numeric(score["final_MIPS_score"], errors="coerce")
    score["Quality_category_score"] = pd.to_numeric(score["Quality_category_score"], errors="coerce")
    score = score.groupby("NPI", as_index=False).agg(mips_score=("final_MIPS_score", "max"), quality_category_score=("Quality_category_score", "max"))

    affiliation = npi(clean_columns(pd.read_csv(args.sources_dir / "Facility_Affiliation.csv", dtype="string", keep_default_na=False)))
    affiliation_summary = affiliation.groupby("NPI", as_index=False).agg(
        affiliated_facility_count=("facility_type", "size"),
        affiliated_facility_types=("facility_type", lambda s: "|".join(sorted(s.dropna().unique())))
    )
    catalog = provider.merge(score, on="NPI", how="left").merge(affiliation_summary, on="NPI", how="left")
    catalog["quality_data_available"] = catalog["mips_score"].notna().astype("int8")
    catalog["affiliated_facility_count"] = catalog["affiliated_facility_count"].fillna(0).astype("int16")
    catalog["affiliated_facility_types"] = catalog["affiliated_facility_types"].fillna("")
    catalog.to_csv(args.output_dir / "provider_catalog.csv", index=False)
    report = {"providers": len(catalog), "telehealth": catalog["telehealth_available"].value_counts(dropna=False).to_dict(), "quality_data_available_rate": round(float(catalog["quality_data_available"].mean()), 4), "affiliation_rate": round(float(catalog["affiliated_facility_count"].gt(0).mean()), 4), "ranking_policy": "Filter strictly by requested state/specialty/telehealth when supplied; rank remaining choices using available MIPS score plus transparent match signals. Missing quality is neutral, not a penalty."}
    (args.output_dir / "provider_catalog_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
