import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.metrics import confusion_matrix, accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, brier_score_loss
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from xgboost import XGBClassifier
import json

root = Path(r"d:\cognizant-hackathon-main")

print("Loading data...")
df = pd.read_csv(root / "model_training_data" / "model_features.csv", parse_dates=["index_date"])
events = pd.read_csv(root / "cleaned_model_inputs" / "claim_events_clean.csv", dtype=str, parse_dates=["start_date", "admission_date", "discharge_date"])
members = pd.read_csv(root / "cleaned_model_inputs" / "member_year_clean.csv", dtype=str)

print("Preparing new features...")
# 1. Ratios
df['ed_to_outpatient_ratio_365d'] = df['ed_visits_365d'] / (df['outpatient_visits_365d'] + 1)
df['acute_cost_velocity_90d'] = df['total_paid_30d'] / (df['total_paid_90d'] + 1)

# 2. ESRD
members['BENE_ESRD_IND'] = members['BENE_ESRD_IND'].eq('Y').astype(int)
members['index_year'] = pd.to_numeric(members['coverage_year'], errors='coerce')
df = df.merge(members[['member_id', 'index_year', 'BENE_ESRD_IND']], on=['member_id', 'index_year'], how='left')
df['BENE_ESRD_IND'] = df['BENE_ESRD_IND'].fillna(0)

# 3. Provider count & 4. Recent inpatient LOS
events['start_date'] = pd.to_datetime(events['start_date'], errors='coerce')
events['event_date'] = events['start_date'].dt.normalize()
events['is_inpatient'] = events['encounter_type'].eq('INPATIENT')

# Ensure we have datetime
events['discharge_date'] = pd.to_datetime(events['discharge_date'], errors='coerce')
events['admission_date'] = pd.to_datetime(events['admission_date'], errors='coerce')
events['los'] = (events['discharge_date'] - events['admission_date']).dt.days.fillna(0)

provider_counts = []
recent_los = []

# Group events by member
histories = {member_id: group for member_id, group in events.groupby('member_id')}

for _, row in df.iterrows():
    m = row['member_id']
    idx_dt = row['index_date']
    if m in histories:
        hist = histories[m]
        
        # Provider count 365d
        # event_date >= (idx_dt - 365d) AND event_date < idx_dt
        mask_365 = (hist['event_date'] >= (idx_dt - pd.Timedelta(days=365))) & (hist['event_date'] < idx_dt)
        prov_count = hist.loc[mask_365, 'provider_npi'].nunique()
        
        # Recent inpatient LOS
        # is_inpatient AND discharge_date < idx_dt
        mask_inp = hist['is_inpatient'] & (hist['discharge_date'] < idx_dt)
        inp_hist = hist.loc[mask_inp]
        if len(inp_hist) > 0:
            # most recent by discharge_date
            last_stay = inp_hist.loc[inp_hist['discharge_date'].idxmax()]
            los = last_stay['los']
        else:
            los = 0
    else:
        prov_count = 0
        los = 0
        
    provider_counts.append(prov_count)
    recent_los.append(los)

df['distinct_provider_count_365d'] = provider_counts
df['recent_inpatient_los'] = recent_los

# Save experimental features
exp_features_path = root / "model_training_data" / "experimental_model_features.csv"
df.to_csv(exp_features_path, index=False)

print("Training models...")

base_model = joblib.load(root / "model_artifacts" / "repeat_ed_risk_model.joblib")
if hasattr(base_model, 'feature_names_in_'):
    base_features = list(base_model.feature_names_in_)
else:
    base_features = base_model.named_steps['model'].get_booster().feature_names

new_features = [
    'BENE_ESRD_IND',
    'distinct_provider_count_365d',
    'ed_to_outpatient_ratio_365d',
    'acute_cost_velocity_90d',
    'recent_inpatient_los'
]
exp_features = base_features + new_features

train_df = df[df['split'] == 'train']
test_df = df[df['split'] == 'test']

X_train_exp = train_df[exp_features]
y_train = train_df['repeat_ed_within_90d']
X_test_exp = test_df[exp_features]
y_test = test_df['repeat_ed_within_90d']

# Exact same configuration as original
# The original used: Pipeline(steps=[('imputer', SimpleImputer(add_indicator=True, strategy='median')), ('model', XGBClassifier(base_score=None, ...))])
# We will use simple imputer median + xgboost defaults but we need to check scale_pos_weight
exp_pipeline = Pipeline([
    ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
    ("model", XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        random_state=42
    ))
])

exp_pipeline.fit(X_train_exp, y_train)
exp_model_path = root / "model_artifacts" / "experimental_repeat_ed_risk_model.joblib"
joblib.dump(exp_pipeline, exp_model_path)

print("Evaluating...")

def evaluate(model, X, y, threshold=0.1746):
    probs = model.predict_proba(X)[:, 1]
    preds = (probs >= threshold).astype(int)
    
    cm = confusion_matrix(y, preds).ravel()
    return {
        'precision': precision_score(y, preds, zero_division=0),
        'recall': recall_score(y, preds, zero_division=0),
        'f1': f1_score(y, preds, zero_division=0),
        'roc_auc': roc_auc_score(y, probs),
        'pr_auc': average_precision_score(y, probs),
        'specificity': cm[0] / (cm[0] + cm[1]) if (cm[0]+cm[1])>0 else 0,
        'brier': brier_score_loss(y, probs),
        'cm': cm,
        'probs': probs
    }

X_test_base = test_df[base_features]
base_res = evaluate(base_model, X_test_base, y_test)
exp_res = evaluate(exp_pipeline, X_test_exp, y_test)

b = exp_pipeline.named_steps['model'].get_booster()
imp = b.get_score(importance_type='gain')
imp_sorted = sorted(imp.items(), key=lambda x: x[1], reverse=True)

report = {
    'baseline': {
        'precision': float(base_res['precision']),
        'recall': float(base_res['recall']),
        'f1': float(base_res['f1']),
        'roc_auc': float(base_res['roc_auc']),
        'pr_auc': float(base_res['pr_auc']),
        'specificity': float(base_res['specificity']),
        'brier': float(base_res['brier'])
    },
    'experimental': {
        'precision': float(exp_res['precision']),
        'recall': float(exp_res['recall']),
        'f1': float(exp_res['f1']),
        'roc_auc': float(exp_res['roc_auc']),
        'pr_auc': float(exp_res['pr_auc']),
        'specificity': float(exp_res['specificity']),
        'brier': float(exp_res['brier'])
    },
    'importance': {k: float(v) for k, v in imp_sorted},
    'train_samples': int(len(train_df)),
    'test_samples': int(len(test_df)),
    'pos_distribution_test': int(y_test.sum()),
    'neg_distribution_test': int(len(y_test) - y_test.sum()),
    'num_base_features': len(base_features),
    'num_exp_features': len(exp_features)
}

with open(root / "experiment_report.json", "w") as f:
    json.dump(report, f, indent=2)

print("Done.")
