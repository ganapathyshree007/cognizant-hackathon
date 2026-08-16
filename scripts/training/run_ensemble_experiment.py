import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, brier_score_loss
from sklearn.model_selection import TimeSeriesSplit, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from catboost import CatBoostClassifier
from sklearn.base import clone
import json

root = Path(r"d:\cognizant-hackathon-main")

print("Loading data...")
df = pd.read_csv(root / "UC07_final_40_features.csv", parse_dates=["index_date"])
df = df.sort_values(['index_date', 'member_id'])

train_df = df[df['split'] == 'train'].copy()
test_df = df[df['split'] == 'test'].copy()

features = [c for c in df.columns if c not in ['member_id', 'index_date', 'index_year', 'split', 'repeat_ed_within_90d', 'excluded_death_in_target_window']]
y_train = train_df['repeat_ed_within_90d']
y_test = test_df['repeat_ed_within_90d']
X_train = train_df[features]
X_test = test_df[features]

log_pipe = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler()),
    ('model', LogisticRegression(max_iter=1000, random_state=42, class_weight='balanced'))
])

cat_pipe = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('model', CatBoostClassifier(iterations=100, depth=4, learning_rate=0.1, random_seed=42, auto_class_weights='Balanced', verbose=0))
])

tscv = TimeSeriesSplit(n_splits=3)

print("Generating Out-of-Fold Predictions...")
oof_log = []
oof_cat = []
y_oof = []

for train_idx, val_idx in tscv.split(X_train):
    X_tr, y_tr = X_train.iloc[train_idx], y_train.iloc[train_idx]
    X_val, y_val = X_train.iloc[val_idx], y_train.iloc[val_idx]
    
    # Train Logistic
    l_pipe = clone(log_pipe)
    l_pipe.fit(X_tr, y_tr)
    oof_log.extend(l_pipe.predict_proba(X_val)[:, 1])
    
    # Train CatBoost
    c_pipe = clone(cat_pipe)
    c_pipe.fit(X_tr, y_tr)
    oof_cat.extend(c_pipe.predict_proba(X_val)[:, 1])
    
    y_oof.extend(y_val)

oof_log = np.array(oof_log)
oof_cat = np.array(oof_cat)
y_oof = np.array(y_oof)

def evaluate(probs, y):
    preds = (probs >= 0.5).astype(int)
    cm = confusion_matrix(y, preds).ravel()
    tn, fp, fn, tp = cm
    return {
        'Precision': float(precision_score(y, preds, zero_division=0)),
        'Recall': float(recall_score(y, preds, zero_division=0)),
        'F1': float(f1_score(y, preds, zero_division=0)),
        'PR-AUC': float(average_precision_score(y, probs)),
        'ROC-AUC': float(roc_auc_score(y, probs)),
        'Specificity': float(tn / (tn + fp) if (tn+fp)>0 else 0),
        'Brier': float(brier_score_loss(y, probs)),
        'cm': {'tn': int(tn), 'fp': int(fp), 'fn': int(fn), 'tp': int(tp)},
        'preds': preds
    }

print("Evaluating OOF Baselines...")
res_oof_log = evaluate(oof_log, y_oof)
res_oof_cat = evaluate(oof_cat, y_oof)

print("Error Complementarity...")
corr = np.corrcoef(oof_log, oof_cat)[0, 1]

cat_correct = (res_oof_cat['preds'] == y_oof)
log_correct = (res_oof_log['preds'] == y_oof)

correct_both = cat_correct & log_correct
cat_only = cat_correct & ~log_correct
log_only = log_correct & ~cat_correct
missed_both = ~cat_correct & ~log_correct

n_total = len(y_oof)
complementarity = {
    'correlation': float(corr),
    'correct_both': int(correct_both.sum()),
    'correct_both_pct': float(correct_both.mean()),
    'cat_only': int(cat_only.sum()),
    'cat_only_pct': float(cat_only.mean()),
    'log_only': int(log_only.sum()),
    'log_only_pct': float(log_only.mean()),
    'missed_both': int(missed_both.sum()),
    'missed_both_pct': float(missed_both.mean()),
}

print("Weighted Ensemble Sweep...")
weights = np.arange(0.1, 1.0, 0.1)
best_weight_cat = 1.0
best_pr_auc = res_oof_cat['PR-AUC']
ensemble_sweep = []

for w_cat in weights:
    w_log = 1.0 - w_cat
    p_ens = w_cat * oof_cat + w_log * oof_log
    res_ens = evaluate(p_ens, y_oof)
    ensemble_sweep.append({
        'w_cat': float(w_cat),
        'w_log': float(w_log),
        'PR-AUC': res_ens['PR-AUC'],
        'F1': res_ens['F1'],
        'ROC-AUC': res_ens['ROC-AUC']
    })
    if res_ens['PR-AUC'] > best_pr_auc:
        best_pr_auc = res_ens['PR-AUC']
        best_weight_cat = w_cat

if best_weight_cat == 1.0: # Check if log is better alone
    if res_oof_log['PR-AUC'] > best_pr_auc:
        best_weight_cat = 0.0

best_weight_log = 1.0 - best_weight_cat
best_oof_ens = best_weight_cat * oof_cat + best_weight_log * oof_log
res_oof_ens = evaluate(best_oof_ens, y_oof)

print("Stacking...")
stacker = LogisticRegression(random_state=42)
X_oof_stack = np.column_stack((oof_cat, oof_log))
stacker.fit(X_oof_stack, y_oof)
oof_stack_probs = stacker.predict_proba(X_oof_stack)[:, 1]
res_oof_stack = evaluate(oof_stack_probs, y_oof)

print("Final Models Training...")
log_pipe.fit(X_train, y_train)
cat_pipe.fit(X_train, y_train)

# Generate final test probabilities
p_test_log = log_pipe.predict_proba(X_test)[:, 1]
p_test_cat = cat_pipe.predict_proba(X_test)[:, 1]
p_test_ens = best_weight_cat * p_test_cat + best_weight_log * p_test_log
X_test_stack = np.column_stack((p_test_cat, p_test_log))
p_test_stack = stacker.predict_proba(X_test_stack)[:, 1]

print("Final Test Evaluation...")
res_test_log = evaluate(p_test_log, y_test)
res_test_cat = evaluate(p_test_cat, y_test)
res_test_ens = evaluate(p_test_ens, y_test)
res_test_stack = evaluate(p_test_stack, y_test)

results = {
    'oof': {
        'Logistic': res_oof_log,
        'CatBoost': res_oof_cat,
        'Weighted_Ensemble': res_oof_ens,
        'Stacking': res_oof_stack
    },
    'test': {
        'Logistic': res_test_log,
        'CatBoost': res_test_cat,
        'Weighted_Ensemble': res_test_ens,
        'Stacking': res_test_stack
    },
    'complementarity': complementarity,
    'best_weights': {'CatBoost': best_weight_cat, 'Logistic': best_weight_log},
    'sweep': ensemble_sweep
}

# Delete preds arrays for json
for res_dict in [results['oof'], results['test']]:
    for m in res_dict.values():
        del m['preds']

with open(root / "ensemble_report.json", "w") as f:
    json.dump(results, f, indent=2)

csv_rows = []
for name, m in results['test'].items():
    row = {'Model': name}
    row.update({k:v for k,v in m.items() if k != 'cm'})
    csv_rows.append(row)
pd.DataFrame(csv_rows).to_csv(root / 'UC07_ENSEMBLE_RESULTS_STAGE_03.csv', index=False)

# Save models
joblib.dump(log_pipe, root / "experimental_logistic_stage03.joblib")
joblib.dump(cat_pipe, root / "experimental_catboost_stage03.joblib")
joblib.dump({
    'catboost': cat_pipe,
    'logistic': log_pipe,
    'weights': {'cat': best_weight_cat, 'log': best_weight_log}
}, root / "experimental_catboost_logistic_ensemble_stage03.joblib")
joblib.dump({
    'catboost': cat_pipe,
    'logistic': log_pipe,
    'stacker': stacker
}, root / "experimental_catboost_logistic_stacking_stage03.joblib")

print("Done.")
