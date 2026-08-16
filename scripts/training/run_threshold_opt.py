import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.metrics import confusion_matrix, accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, brier_score_loss
from sklearn.model_selection import TimeSeriesSplit, cross_val_predict
from sklearn.base import clone
from sklearn.utils import resample
import json

root = Path(r"d:\cognizant-hackathon-main")

print("Loading data...")
df = pd.read_csv(root / "model_training_data" / "experimental_model_features.csv", parse_dates=["index_date"])
df = df.sort_values(['index_date', 'member_id'])

train_df = df[df['split'] == 'train'].copy()
test_df = df[df['split'] == 'test'].copy()

y_train = train_df['repeat_ed_within_90d']
y_test = test_df['repeat_ed_within_90d']

# Load models
base_model = joblib.load(root / "model_artifacts" / "repeat_ed_risk_model.joblib")
exp_model = joblib.load(root / "model_artifacts" / "experimental_xgboost_model_v03.joblib")

if hasattr(base_model, 'feature_names_in_'):
    base_features = list(base_model.feature_names_in_)
else:
    base_features = base_model.named_steps['model'].get_booster().feature_names

if hasattr(exp_model, 'feature_names_in_'):
    exp_features = list(exp_model.feature_names_in_)
else:
    exp_features = exp_model.named_steps['model'].get_booster().feature_names

X_train_base = train_df[base_features]
X_test_base = test_df[base_features]
X_train_exp = train_df[exp_features]
X_test_exp = test_df[exp_features]

from sklearn.model_selection import StratifiedKFold
print("Generating Out-of-Fold Predictions for Threshold Tuning...")
tscv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
model_clone = clone(exp_model)
oof_probs = cross_val_predict(model_clone, X_train_exp, y_train, cv=tscv, method='predict_proba', n_jobs=-1)[:, 1]

y_oof = y_train.values

# Threshold sweep
thresholds = np.arange(0.01, 0.405, 0.005)
sweep_results = []
for t in thresholds:
    preds = (oof_probs >= t).astype(int)
    cm = confusion_matrix(y_oof, preds).ravel() # tn, fp, fn, tp
    tn, fp, fn, tp = cm
    
    prec = precision_score(y_oof, preds, zero_division=0)
    rec = recall_score(y_oof, preds, zero_division=0)
    f1 = f1_score(y_oof, preds, zero_division=0)
    spec = tn / (tn + fp) if (tn + fp) > 0 else 0
    fpr = fp / (tn + fp) if (tn + fp) > 0 else 0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0
    ppr = (tp + fp) / len(y_oof)
    
    sweep_results.append({
        'Threshold': round(t, 3),
        'Precision': float(prec),
        'Recall': float(rec),
        'F1': float(f1),
        'Specificity': float(spec),
        'FPR': float(fpr),
        'FNR': float(fnr),
        'PositiveRate': float(ppr)
    })

sweep_df = pd.DataFrame(sweep_results)
sweep_df.to_csv(root / 'UC07_THRESHOLD_RESULTS.csv', index=False)

# Identify Candidates
best_f1_idx = sweep_df['F1'].idxmax()
best_f1_thresh = sweep_df.loc[best_f1_idx, 'Threshold']

best_prec_idx = sweep_df['Precision'].idxmax()
best_prec_thresh = sweep_df.loc[best_prec_idx, 'Threshold']

best_rec_idx = sweep_df['Recall'].idxmax()
best_rec_thresh = sweep_df.loc[best_rec_idx, 'Threshold']

# For "best balance", look for min |Precision - Recall| among top F1s
# Or just use max F1
selected_threshold = float(best_f1_thresh)

print(f"Selected Threshold: {selected_threshold}")
with open(root / "experimental_threshold_v04.json", "w") as f:
    json.dump({"best_f1_threshold": selected_threshold}, f)

# Final Test Evaluation
def evaluate(model, X, y, threshold):
    probs = model.predict_proba(X)[:, 1]
    preds = (probs >= threshold).astype(int)
    cm = confusion_matrix(y, preds).ravel()
    return {
        'precision': float(precision_score(y, preds, zero_division=0)),
        'recall': float(recall_score(y, preds, zero_division=0)),
        'f1': float(f1_score(y, preds, zero_division=0)),
        'roc_auc': float(roc_auc_score(y, probs)),
        'pr_auc': float(average_precision_score(y, probs)),
        'specificity': float(cm[0] / (cm[0] + cm[1]) if (cm[0]+cm[1])>0 else 0),
        'brier': float(brier_score_loss(y, probs)),
        'accuracy': float(accuracy_score(y, preds)),
        'ppr': float((preds == 1).sum() / len(preds)),
        'cm': {'tn': int(cm[0]), 'fp': int(cm[1]), 'fn': int(cm[2]), 'tp': int(cm[3])},
        'preds': preds
    }

print("Final Test Evaluation...")
base_res = evaluate(base_model, X_test_base, y_test, 0.1746)
exp_res = evaluate(exp_model, X_test_exp, y_test, selected_threshold)

# Error analysis
base_preds = base_res['preds']
exp_preds = exp_res['preds']

recovered_fns = sum((y_test == 1) & (base_preds == 0) & (exp_preds == 1))
new_fps = sum((y_test == 0) & (base_preds == 0) & (exp_preds == 1))
lost_tps = sum((y_test == 1) & (base_preds == 1) & (exp_preds == 0))
fixed_fps = sum((y_test == 0) & (base_preds == 1) & (exp_preds == 0))

# Bootstrapping for CI (100 iterations for speed)
np.random.seed(42)
boot_metrics = {'prec': [], 'rec': [], 'f1': [], 'pr_auc': []}
for i in range(100):
    idx = resample(np.arange(len(y_test)), random_state=i)
    y_boot = y_test.iloc[idx]
    X_boot = X_test_exp.iloc[idx]
    res_b = evaluate(exp_model, X_boot, y_boot, selected_threshold)
    boot_metrics['prec'].append(res_b['precision'])
    boot_metrics['rec'].append(res_b['recall'])
    boot_metrics['f1'].append(res_b['f1'])
    boot_metrics['pr_auc'].append(res_b['pr_auc'])

ci = {
    'precision': [np.percentile(boot_metrics['prec'], 2.5), np.percentile(boot_metrics['prec'], 97.5)],
    'recall': [np.percentile(boot_metrics['rec'], 2.5), np.percentile(boot_metrics['rec'], 97.5)],
    'f1': [np.percentile(boot_metrics['f1'], 2.5), np.percentile(boot_metrics['f1'], 97.5)],
    'pr_auc': [np.percentile(boot_metrics['pr_auc'], 2.5), np.percentile(boot_metrics['pr_auc'], 97.5)]
}

del base_res['preds']
del exp_res['preds']

report = {
    'baseline': base_res,
    'experimental': exp_res,
    'threshold': selected_threshold,
    'candidates': {
        'max_f1': best_f1_thresh,
        'max_prec': best_prec_thresh,
        'max_rec': best_rec_thresh
    },
    'error_analysis': {
        'recovered_fns': int(recovered_fns),
        'new_fps': int(new_fps),
        'lost_tps': int(lost_tps),
        'fixed_fps': int(fixed_fps)
    },
    'ci_95': {k: [float(v[0]), float(v[1])] for k,v in ci.items()}
}

with open(root / "threshold_report.json", "w") as f:
    json.dump(report, f, indent=2)

print("Done.")
