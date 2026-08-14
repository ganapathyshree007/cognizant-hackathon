"""Fast, non-destructive CMS preparation using the existing collapsed pipeline output.

This is the deployment input layer. It does not alter raw CMS files and it does
not impute clinically meaningful missing values with zero.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


ED_PATTERN = r"(?:^|\|)9928[1-5](?:\||$)"
NULL_TOKENS = {"", " ", "NA", "N/A", "NULL", "None", "nan"}


def text_clean(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().replace(list(NULL_TOKENS), pd.NA)


def clean_events(pipeline_dir: Path) -> tuple[pd.DataFrame, dict]:
    raw = pd.read_csv(pipeline_dir / "unified_encounters.csv", dtype="string", keep_default_na=False)
    rows_before = len(raw)
    data = raw.copy()
    for column in ["member_id", "claim_id", "encounter_type", "provider_id", "provider_npi", "diagnosis_codes", "procedure_codes", "hcpcs_codes", "drg_code"]:
        data[column] = text_clean(data[column])
    for column in ["start_date", "end_date", "admission_date", "discharge_date"]:
        original = text_clean(data[column])
        parsed = pd.to_datetime(original, errors="coerce")
        data[column] = parsed
        data[f"{column}_invalid_flag"] = (original.notna() & parsed.isna()).astype("int8")
    data["payment_amount"] = pd.to_numeric(data["payment_amount"], errors="coerce")
    data["payment_amount_invalid_flag"] = (text_clean(raw["payment_amount"]).notna() & data["payment_amount"].isna()).astype("int8")
    data = data.dropna(subset=["member_id", "claim_id", "encounter_type"])
    data = data.drop_duplicates(subset=["member_id", "claim_id", "encounter_type"])
    data["date_missing_flag"] = data["start_date"].isna().astype("int8")
    data["ed_candidate_flag"] = data["hcpcs_codes"].fillna("").str.contains(ED_PATTERN, regex=True).astype("int8")
    # `provider_npi` in the original collapsed file may represent only one of several claim providers.
    data["provider_link_status"] = "use_claim_provider_clean_for_provider_analysis"
    report = {
        "dataset": "claim_events",
        "rows_before": rows_before,
        "rows_after": len(data),
        "rows_removed_missing_core_key_or_duplicate": rows_before - len(data),
        "ed_candidate_events": int(data["ed_candidate_flag"].sum()),
        "invalid_dates": {c: int(data[f"{c}_invalid_flag"].sum()) for c in ["start_date", "end_date", "admission_date", "discharge_date"]},
        "missing_percent": {c: round(float(data[c].isna().mean() * 100), 3) for c in data.columns},
    }
    return data, report


def clean_members(raw_dir: Path) -> tuple[pd.DataFrame, list[dict]]:
    all_years, reports = [], []
    for year in (2008, 2009, 2010):
        raw = pd.read_csv(raw_dir / f"DE1_0_{year}_Beneficiary_Summary_File_Sample_1.csv", dtype="string", keep_default_na=False)
        data = raw.copy()
        for column in data.columns:
            data[column] = text_clean(data[column])
        birth = pd.to_datetime(data["BENE_BIRTH_DT"], format="%Y%m%d", errors="coerce")
        death = pd.to_datetime(data["BENE_DEATH_DT"], format="%Y%m%d", errors="coerce")
        data["member_id"] = data["DESYNPUF_ID"]
        data["coverage_year"] = year
        data["birth_date"] = birth
        data["death_date"] = death
        data["has_recorded_death"] = death.notna().astype("int8")
        data["age_at_year_end"] = year - birth.dt.year
        before = len(data)
        data = data.dropna(subset=["member_id", "birth_date"]).drop_duplicates(subset=["member_id", "coverage_year"])
        all_years.append(data)
        reports.append({"dataset": f"member_year_{year}", "rows_before": before, "rows_after": len(data), "invalid_birth_dates": int((data["BENE_BIRTH_DT"].notna() & data["birth_date"].isna()).sum())})
    return pd.concat(all_years, ignore_index=True), reports


def clean_provider_roles(raw_dir: Path) -> pd.DataFrame:
    parts = []
    sources = [
        ("DE1_0_2008_to_2010_Inpatient_Claims_Sample_1.csv", "INPATIENT"),
        ("DE1_0_2008_to_2010_Outpatient_Claims_Sample_1.csv", "OUTPATIENT"),
    ]
    for filename, encounter_type in sources:
        raw = pd.read_csv(raw_dir / filename, dtype="string", keep_default_na=False,
                          usecols=["DESYNPUF_ID", "CLM_ID", "AT_PHYSN_NPI", "OP_PHYSN_NPI", "OT_PHYSN_NPI"])
        raw = raw.rename(columns={"DESYNPUF_ID": "member_id", "CLM_ID": "claim_id"})
        for source_column, role in [("AT_PHYSN_NPI", "attending"), ("OP_PHYSN_NPI", "operating"), ("OT_PHYSN_NPI", "other")]:
            part = raw[["member_id", "claim_id", source_column]].copy()
            part["npi"] = text_clean(part.pop(source_column)).str.replace(r"\.0$", "", regex=True).str.replace(r"\D", "", regex=True)
            part = part[part["npi"].str.len().between(1, 10, inclusive="both")]
            part["npi"] = part["npi"].str.zfill(10)
            part["provider_role"] = role
            part["encounter_type"] = encounter_type
            parts.append(part)
    return pd.concat(parts, ignore_index=True).drop_duplicates()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--pipeline-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    events, event_report = clean_events(args.pipeline_dir)
    members, member_reports = clean_members(args.raw_dir)
    provider_roles = clean_provider_roles(args.raw_dir)
    events.to_csv(args.output_dir / "claim_events_clean.csv", index=False)
    members.to_csv(args.output_dir / "member_year_clean.csv", index=False)
    provider_roles.to_csv(args.output_dir / "claim_provider_clean.csv", index=False)
    quality = {"claim_events": event_report, "members": member_reports, "claim_provider_rows": len(provider_roles)}
    (args.output_dir / "data_quality_report.json").write_text(json.dumps(quality, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"claim_events": len(events), "member_year": len(members), "claim_provider": len(provider_roles)}, indent=2))


if __name__ == "__main__":
    main()
