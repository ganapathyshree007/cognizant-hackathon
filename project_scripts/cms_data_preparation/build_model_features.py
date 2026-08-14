"""Build a leakage-free CMS training table for repeat ED utilization.

One row represents one member's ED-candidate day. All utilization features use
only events strictly before the index date. The label is a new ED-candidate day
within the next 90 days. This script never modifies the source data.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


LOOKBACKS = (30, 90, 365)
CHRONIC_COLUMNS = ["SP_ALZHDMTA", "SP_CHF", "SP_CHRNKIDN", "SP_CNCR", "SP_COPD", "SP_DEPRESSN", "SP_DIABETES", "SP_ISCHMCHT", "SP_OSTEOPRS", "SP_RA_OA", "SP_STRKETIA"]


def window_sum(dates: np.ndarray, values: np.ndarray, index_day: np.datetime64, days: int) -> float:
    left = np.searchsorted(dates, index_day - np.timedelta64(days, "D"), side="left")
    right = np.searchsorted(dates, index_day, side="left")  # strict: the index-day event is never a feature
    return float(values[left:right].sum())


def future_ed(ed_dates: np.ndarray, index_day: np.datetime64) -> int:
    start = np.searchsorted(ed_dates, index_day, side="right")
    end = np.searchsorted(ed_dates, index_day + np.timedelta64(90, "D"), side="right")
    return int(end > start)


def event_features(events: pd.DataFrame) -> pd.DataFrame:
    events = events.dropna(subset=["start_date"]).copy()
    events["event_date"] = events["start_date"].dt.normalize()
    events["payment_amount"] = events["payment_amount"].fillna(0.0).clip(lower=0)
    events["is_outpatient"] = events["encounter_type"].eq("OUTPATIENT").astype("int8")
    events["is_inpatient"] = events["encounter_type"].eq("INPATIENT").astype("int8")
    events["has_diagnosis"] = events["diagnosis_codes"].notna().astype("int8")

    # One ED index per member/day: it prevents duplicate same-day billing lines becoming duplicate training rows.
    ed_index = events.loc[events["ed_candidate_flag"].eq(1), ["member_id", "event_date"]].drop_duplicates()
    cutoff = events["event_date"].max() - pd.Timedelta(days=90)
    ed_index = ed_index.loc[ed_index["event_date"].le(cutoff)].copy()

    outputs = []
    events = events.sort_values(["member_id", "event_date"])
    # Build the member histories once. Re-filtering the complete event table for
    # every member is prohibitively slow and does not change the calculation.
    histories = {member_id: group.reset_index(drop=True) for member_id, group in events.groupby("member_id", sort=False)}
    for member_id, index_group in ed_index.groupby("member_id", sort=False):
        history = histories[member_id]
        dates = history["event_date"].values.astype("datetime64[D]")
        ed_dates = history.loc[history["ed_candidate_flag"].eq(1), "event_date"].drop_duplicates().values.astype("datetime64[D]")
        arrays = {
            "all_visits": np.ones(len(history), dtype=np.int16),
            "ed_visits": history["ed_candidate_flag"].to_numpy(dtype=np.int16),
            "outpatient_visits": history["is_outpatient"].to_numpy(dtype=np.int16),
            "inpatient_visits": history["is_inpatient"].to_numpy(dtype=np.int16),
            "total_paid": history["payment_amount"].to_numpy(dtype=float),
            "diagnosis_coded_visits": history["has_diagnosis"].to_numpy(dtype=np.int16),
        }
        for day in index_group["event_date"].values.astype("datetime64[D]"):
            row = {"member_id": member_id, "index_date": pd.Timestamp(day), "index_year": int(pd.Timestamp(day).year)}
            prior_end = np.searchsorted(dates, day, side="left")
            row["days_since_previous_event"] = int((day - dates[prior_end - 1]).astype("timedelta64[D]").astype(int)) if prior_end else np.nan
            prior_ed = ed_dates[ed_dates < day]
            row["days_since_previous_ed"] = int((day - prior_ed[-1]).astype("timedelta64[D]").astype(int)) if len(prior_ed) else np.nan
            for window in LOOKBACKS:
                for name, values in arrays.items():
                    row[f"{name}_{window}d"] = window_sum(dates, values, day, window)
            row["repeat_ed_within_90d"] = future_ed(ed_dates, day)
            outputs.append(row)
    return pd.DataFrame(outputs)


def member_features(members: pd.DataFrame) -> pd.DataFrame:
    members = members.copy()
    keep = ["member_id", "coverage_year", "age_at_year_end", "BENE_HI_CVRAGE_TOT_MONS", "BENE_SMI_CVRAGE_TOT_MONS", "BENE_HMO_CVRAGE_TOT_MONS", "PLAN_CVRG_MOS_NUM", "death_date"] + CHRONIC_COLUMNS
    members = members[keep]
    members = members.rename(columns={"coverage_year": "index_year"})
    members["index_year"] = pd.to_numeric(members["index_year"], errors="coerce").astype("Int64")
    for column in CHRONIC_COLUMNS:
        members[column.replace("SP_", "chronic_").lower()] = members[column].eq("1").astype("int8")
    chronic_flags = [c.replace("SP_", "chronic_").lower() for c in CHRONIC_COLUMNS]
    members["chronic_condition_burden"] = members[chronic_flags].sum(axis=1)
    members = members.drop(columns=CHRONIC_COLUMNS)
    numeric = ["age_at_year_end", "BENE_HI_CVRAGE_TOT_MONS", "BENE_SMI_CVRAGE_TOT_MONS", "BENE_HMO_CVRAGE_TOT_MONS", "PLAN_CVRG_MOS_NUM"]
    members[numeric] = members[numeric].apply(pd.to_numeric, errors="coerce")
    return members.drop_duplicates(["member_id", "index_year"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    events = pd.read_csv(args.input_dir / "claim_events_clean.csv", dtype={"member_id": "string", "claim_id": "string"}, parse_dates=["start_date", "end_date"])
    members = pd.read_csv(args.input_dir / "member_year_clean.csv", dtype="string", parse_dates=["death_date"])
    feature_table = event_features(events)
    feature_table = feature_table.merge(member_features(members), on=["member_id", "index_year"], how="left", validate="many_to_one")

    # Death within the target horizon means the member cannot be labeled as a true "no return".
    death_in_horizon = feature_table["death_date"].notna() & feature_table["death_date"].le(feature_table["index_date"] + pd.Timedelta(days=90))
    feature_table["excluded_death_in_target_window"] = death_in_horizon.astype("int8")
    feature_table = feature_table.loc[~death_in_horizon].drop(columns=["death_date"])
    feature_table["split"] = np.select(
        [feature_table["index_year"].eq(2008), feature_table["index_year"].eq(2009), feature_table["index_year"].eq(2010)],
        ["train", "train", "test"], default="exclude"
    )
    feature_table = feature_table.sort_values(["index_date", "member_id"]).reset_index(drop=True)
    feature_table.to_csv(args.output_dir / "model_features.csv", index=False)

    report = {
        "outcome": "repeat ED-candidate event strictly after index date and within 90 days",
        "feature_policy": "all utilization features use only events strictly before index_date",
        "index_unit": "one member ED-candidate day",
        "cutoff_policy": "index dates in the final 90 observed days are excluded",
        "death_policy": "exclude member indexes with recorded death on/before label-horizon end",
        "rows": len(feature_table),
        "positive_rate": round(float(feature_table["repeat_ed_within_90d"].mean()), 5),
        "split_counts": feature_table["split"].value_counts().to_dict(),
        "missing_member_year_features": int(feature_table["age_at_year_end"].isna().sum()),
        "columns": list(feature_table.columns),
    }
    (args.output_dir / "model_features_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
