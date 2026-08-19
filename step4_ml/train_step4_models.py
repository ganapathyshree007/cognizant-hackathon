"""Leakage-safe repeat-ED model pipeline for the Synthea ``step4_raw`` data.

Creates one example for each emergency encounter.  Features use events strictly
before that encounter and the target is another emergency encounter in the next
90 days.  This is prioritisation support only: it must not be used for triage or
to override the application's Safety Gate and Care Manager review.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (average_precision_score, brier_score_loss,
                             precision_recall_fscore_support, roc_auc_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

RANDOM_SEED = 42
LOOKBACK_DAYS = (30, 90, 365)
TARGET_HORIZON_DAYS = 90


def clean_text(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})


def read_clean_data(raw_dir: Path, output_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Read only columns used by the model, standardise types, and save a QA report."""
    encounters = pd.read_csv(raw_dir / "encounters.csv", dtype="string")
    patients = pd.read_csv(raw_dir / "patients.csv", dtype="string")
    before = {"encounters": len(encounters), "patients": len(patients)}
    encounters.columns = encounters.columns.str.lower()
    patients.columns = patients.columns.str.lower()
    for frame in (encounters, patients):
        for column in frame.columns:
            if frame[column].dtype.name == "string":
                frame[column] = clean_text(frame[column])

    encounters["start"] = pd.to_datetime(encounters["start"], errors="coerce", utc=True).dt.tz_localize(None)
    encounters["stop"] = pd.to_datetime(encounters["stop"], errors="coerce", utc=True).dt.tz_localize(None)
    for column in ("base_encounter_cost", "total_claim_cost", "payer_coverage"):
        encounters[column] = pd.to_numeric(encounters[column], errors="coerce")
    encounters = encounters.dropna(subset=["id", "patient", "start", "encounterclass"]).drop_duplicates("id")
    encounters["encounterclass"] = encounters["encounterclass"].str.lower()
    patients["birthdate"] = pd.to_datetime(patients["birthdate"], errors="coerce")
    patients["deathdate"] = pd.to_datetime(patients["deathdate"], errors="coerce")
    patients = patients.dropna(subset=["id"]).drop_duplicates("id")
    report = {
        "source": str(raw_dir), "rows_before": before,
        "rows_after": {"encounters": len(encounters), "patients": len(patients)},
        "invalid_or_missing_encounter_start": int(encounters["start"].isna().sum()),
        "emergency_encounters": int(encounters["encounterclass"].eq("emergency").sum()),
        "orphan_encounter_patients": int((~encounters["patient"].isin(patients["id"])).sum()),
        "deduplication": "encounter IDs and patient IDs are unique after cleaning",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    encounters.to_parquet(output_dir / "encounters_clean.parquet", index=False)
    patients.to_parquet(output_dir / "patients_clean.parquet", index=False)
    return encounters, patients, report


def count_in_window(dates: np.ndarray, index_date: np.datetime64, days: int) -> int:
    left = np.searchsorted(dates, index_date - np.timedelta64(days, "D"), side="left")
    right = np.searchsorted(dates, index_date, side="left")
    return int(right - left)


def build_features(encounters: pd.DataFrame, patients: pd.DataFrame) -> pd.DataFrame:
    data = encounters.sort_values(["patient", "start"]).copy()
    data["event_day"] = data["start"].dt.normalize()
    last_label_day = data["event_day"].max() - pd.Timedelta(days=TARGET_HORIZON_DAYS)
    indexes = data.loc[(data["encounterclass"] == "emergency") & (data["event_day"] <= last_label_day), ["id", "patient", "event_day"]]
    rows: list[dict[str, Any]] = []
    histories = {key: group.reset_index(drop=True) for key, group in data.groupby("patient", sort=False)}
    for patient_id, index_rows in indexes.groupby("patient", sort=False):
        history = histories[patient_id]
        all_dates = history["event_day"].values.astype("datetime64[D]")
        emergency_dates = history.loc[history["encounterclass"].eq("emergency"), "event_day"].drop_duplicates().values.astype("datetime64[D]")
        class_dates = {name: group["event_day"].values.astype("datetime64[D]") for name, group in history.groupby("encounterclass")}
        costs = history["total_claim_cost"].fillna(0).clip(lower=0).to_numpy(float)
        for _, index in index_rows.iterrows():
            day = np.datetime64(index.event_day.date())
            prior = np.searchsorted(all_dates, day, side="left")
            previous_ed = emergency_dates[emergency_dates < day]
            row: dict[str, Any] = {"index_encounter_id": index.id, "patient_id": patient_id, "index_date": pd.Timestamp(day)}
            row["days_since_previous_encounter"] = int((day - all_dates[prior - 1]).astype("timedelta64[D]").astype(int)) if prior else np.nan
            row["days_since_previous_ed"] = int((day - previous_ed[-1]).astype("timedelta64[D]").astype(int)) if len(previous_ed) else np.nan
            for window in LOOKBACK_DAYS:
                left, right = np.searchsorted(all_dates, day - np.timedelta64(window, "D"), side="left"), np.searchsorted(all_dates, day, side="left")
                row[f"all_encounters_{window}d"] = int(right - left)
                row[f"claim_cost_{window}d"] = float(costs[left:right].sum())
                for encounter_class in ("emergency", "inpatient", "outpatient", "ambulatory", "urgentcare", "wellness"):
                    dates = class_dates.get(encounter_class, np.array([], dtype="datetime64[D]"))
                    row[f"{encounter_class}_{window}d"] = count_in_window(dates, day, window)
            future_start = np.searchsorted(emergency_dates, day, side="right")
            future_end = np.searchsorted(emergency_dates, day + np.timedelta64(TARGET_HORIZON_DAYS, "D"), side="right")
            row["repeat_ed_within_90d"] = int(future_end > future_start)
            rows.append(row)
    features = pd.DataFrame(rows)
    demographics = patients[["id", "birthdate", "deathdate", "gender", "race", "ethnicity", "marital", "state"]].rename(columns={"id": "patient_id"})
    features = features.merge(demographics, on="patient_id", how="left", validate="many_to_one")
    features["age_at_index"] = ((features["index_date"] - features["birthdate"]).dt.days / 365.25).clip(0, 120)
    death_in_horizon = features["deathdate"].notna() & (features["deathdate"] <= features["index_date"] + pd.Timedelta(days=TARGET_HORIZON_DAYS))
    features = features.loc[~death_in_horizon].drop(columns=["birthdate", "deathdate"])
    return features.sort_values(["index_date", "patient_id"]).reset_index(drop=True)


def temporal_split(data: pd.DataFrame) -> pd.DataFrame:
    years = sorted(data["index_date"].dt.year.unique())
    if len(years) < 3:
        raise ValueError("Need at least three index years for chronological train/validation/test splits.")
    test_year, validation_year = years[-1], years[-2]
    data = data.copy()
    data["split"] = np.where(data["index_date"].dt.year == test_year, "test", np.where(data["index_date"].dt.year == validation_year, "validation", "train"))
    return data


def feature_columns(data: pd.DataFrame) -> tuple[list[str], list[str]]:
    excluded = {"index_encounter_id", "patient_id", "index_date", "repeat_ed_within_90d", "split"}
    columns = [column for column in data.columns if column not in excluded]
    categorical = [column for column in columns if str(data[column].dtype) in ("string", "object")]
    return columns, categorical


def metrics(y_true: pd.Series, probability: np.ndarray) -> dict[str, float | None]:
    prediction = (probability >= 0.5).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, prediction, average="binary", zero_division=0)
    return {"roc_auc": round(float(roc_auc_score(y_true, probability)), 5) if y_true.nunique() > 1 else None,
            "pr_auc": round(float(average_precision_score(y_true, probability)), 5) if y_true.nunique() > 1 else None,
            "precision_at_0_5": round(float(precision), 5), "recall_at_0_5": round(float(recall), 5),
            "f1_at_0_5": round(float(f1), 5), "brier_score": round(float(brier_score_loss(y_true, probability)), 5)}


def train_catboost(train: pd.DataFrame, validation: pd.DataFrame, test: pd.DataFrame, columns: list[str], categorical: list[str], out: Path) -> dict[str, Any]:
    from catboost import CatBoostClassifier
    def prepare(frame: pd.DataFrame) -> pd.DataFrame:
        result = frame[columns].copy()
        for column in categorical: result[column] = result[column].fillna("__MISSING__").astype(str)
        return result
    model = CatBoostClassifier(iterations=500, depth=6, learning_rate=0.04, loss_function="Logloss", eval_metric="PRAUC", random_seed=RANDOM_SEED, verbose=False, auto_class_weights="Balanced", allow_writing_files=False)
    model.fit(prepare(train), train.repeat_ed_within_90d, cat_features=categorical, eval_set=(prepare(validation), validation.repeat_ed_within_90d), early_stopping_rounds=50, verbose=False)
    model.save_model(out / "catboost_repeat_ed.cbm")
    return {"model": "CatBoost", "status": "trained", **metrics(test.repeat_ed_within_90d, model.predict_proba(prepare(test))[:, 1])}


def train_tabpfn(train: pd.DataFrame, test: pd.DataFrame, columns: list[str], categorical: list[str], out: Path) -> dict[str, Any]:
    from tabpfn import TabPFNClassifier
    numeric = [c for c in columns if c not in categorical]
    # Convert pandas' nullable values before scikit-learn sees them.  Passing a
    # pd.NA inside an object array causes an ambiguous-boolean error in its
    # imputer.
    def prepare(frame: pd.DataFrame) -> pd.DataFrame:
        result = frame[columns].copy()
        for column in categorical:
            result[column] = result[column].astype("string").fillna("__MISSING__").astype(object)
        for column in numeric:
            result[column] = pd.to_numeric(result[column], errors="coerce")
        return result
    transformer = ColumnTransformer([("num", Pipeline([("impute", SimpleImputer(strategy="median"))]), [c for c in columns if c not in categorical]), ("cat", Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical)])
    x_train, x_test = transformer.fit_transform(prepare(train)), transformer.transform(prepare(test))
    model = TabPFNClassifier(random_state=RANDOM_SEED, n_estimators=8)
    model.fit(x_train, train.repeat_ed_within_90d)
    import pickle
    with open(out / "tabpfn_repeat_ed.pkl", "wb") as handle: pickle.dump({"transformer": transformer, "model": model}, handle)
    return {"model": "TabPFN-3", "status": "trained", **metrics(test.repeat_ed_within_90d, model.predict_proba(x_test)[:, 1])}


def train_ft_transformer(train: pd.DataFrame, validation: pd.DataFrame, test: pd.DataFrame, columns: list[str], categorical: list[str], out: Path) -> dict[str, Any]:
    # The compact custom implementation avoids an unmaintained third-party wrapper while using PyTorch's TransformerEncoder.
    import torch
    from torch import nn
    torch.manual_seed(RANDOM_SEED); random.seed(RANDOM_SEED); np.random.seed(RANDOM_SEED)
    numeric = [column for column in columns if column not in categorical]
    medians = train[numeric].median(); means = train[numeric].fillna(medians).mean(); stds = train[numeric].fillna(medians).std().replace(0, 1)
    vocabularies = {column: {value: index + 1 for index, value in enumerate(train[column].fillna("__MISSING__").astype(str).unique())} for column in categorical}
    def encode(frame: pd.DataFrame):
        x_num = ((frame[numeric].fillna(medians) - means) / stds).to_numpy(np.float32)
        x_cat = np.column_stack([frame[c].fillna("__MISSING__").astype(str).map(vocabularies[c]).fillna(0).astype(int).to_numpy() for c in categorical]) if categorical else np.empty((len(frame), 0), dtype=int)
        return torch.tensor(x_num), torch.tensor(x_cat), torch.tensor(frame.repeat_ed_within_90d.to_numpy(np.float32))
    class FTTransformer(nn.Module):
        def __init__(self):
            super().__init__(); d = 32
            self.num = nn.Parameter(torch.randn(len(numeric), d) * .02); self.num_bias = nn.Parameter(torch.zeros(len(numeric), d))
            self.embeddings = nn.ModuleList([nn.Embedding(len(vocabularies[c]) + 1, d) for c in categorical]); self.cls = nn.Parameter(torch.zeros(1, 1, d))
            layer = nn.TransformerEncoderLayer(d_model=d, nhead=4, dim_feedforward=64, batch_first=True, dropout=.1)
            self.encoder = nn.TransformerEncoder(layer, num_layers=2); self.head = nn.Sequential(nn.LayerNorm(d), nn.Linear(d, 1))
        def forward(self, x_num, x_cat):
            num_tokens = x_num.unsqueeze(-1) * self.num + self.num_bias
            cat_tokens = [emb(x_cat[:, i]).unsqueeze(1) for i, emb in enumerate(self.embeddings)]
            tokens = torch.cat([self.cls.expand(len(x_num), -1, -1), num_tokens] + cat_tokens, dim=1)
            return self.head(self.encoder(tokens)[:, 0]).squeeze(1)
    model = FTTransformer(); optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-5); loss_fn = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([(len(train) - train.repeat_ed_within_90d.sum()) / max(train.repeat_ed_within_90d.sum(), 1)]))
    xtr, ctr, ytr = encode(train); xval, cval, yval = encode(validation)
    best, best_state, patience = float("inf"), None, 0
    for _ in range(80):
        model.train(); optimizer.zero_grad(); loss = loss_fn(model(xtr, ctr), ytr); loss.backward(); optimizer.step()
        model.eval()
        with torch.no_grad(): value = float(loss_fn(model(xval, cval), yval))
        if value < best: best, best_state, patience = value, {k: v.detach().clone() for k, v in model.state_dict().items()}, 0
        else: patience += 1
        if patience >= 12: break
    model.load_state_dict(best_state); model.eval(); xt, ct, _ = encode(test)
    with torch.no_grad(): probability = torch.sigmoid(model(xt, ct)).numpy()
    torch.save({"state_dict": model.state_dict(), "numeric": numeric, "categorical": categorical, "medians": medians.to_dict(), "means": means.to_dict(), "stds": stds.to_dict(), "vocabularies": vocabularies}, out / "ft_transformer_repeat_ed.pt")
    return {"model": "FT-Transformer", "status": "trained", **metrics(test.repeat_ed_within_90d, probability)}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--raw-dir", type=Path, default=Path("step4_raw")); parser.add_argument("--output-dir", type=Path, default=Path("step4_ml_output")); args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    encounters, patients, quality = read_clean_data(args.raw_dir, args.output_dir)
    data = temporal_split(build_features(encounters, patients)); data.to_parquet(args.output_dir / "repeat_ed_features.parquet", index=False); data.to_csv(args.output_dir / "repeat_ed_features.csv", index=False)
    columns, categorical = feature_columns(data); train, validation, test = (data.loc[data.split == name].copy() for name in ("train", "validation", "test"))
    report: dict[str, Any] = {"purpose": "repeat ED utilisation prioritisation; not clinical triage", "target": "a subsequent emergency encounter within 90 days", "point_in_time_policy": "all feature windows end strictly before index_date", "data_quality": quality, "rows": len(data), "positive_rate": round(float(data.repeat_ed_within_90d.mean()), 5), "splits": data.split.value_counts().to_dict(), "feature_columns": columns, "categorical_columns": categorical, "model_results": []}
    for trainer, name in ((train_catboost, "CatBoost"), (train_ft_transformer, "FT-Transformer"), (train_tabpfn, "TabPFN-3")):
        try:
            result = trainer(train, validation, test, columns, categorical, args.output_dir) if name != "TabPFN-3" else trainer(pd.concat([train, validation]), test, columns, categorical, args.output_dir)
        except Exception as error:
            result = {"model": name, "status": "not_trained", "reason": f"{type(error).__name__}: {error}"}
        report["model_results"].append(result); print(result)
    pd.DataFrame(report["model_results"]).to_csv(args.output_dir / "model_comparison.csv", index=False)
    (args.output_dir / "training_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

if __name__ == "__main__": main()
