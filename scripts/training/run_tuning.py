import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.metrics import confusion_matrix, accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, brier_score_loss, make_scorer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from xgboost import XGBClassifier
from sklearn.model_selection import TimeSeriesSplit, RandomizedSearchCV
import json

root = Path(r"d:\cognizant-hackathon-main")

print("Loading data...")
df = pd.read_csv(root / "model_training_data" / "experimental_model_features.csv", parse_dates=["index_date"])
df = df.sort_values(['index_date', 'member_id'])

train_df = df[df['split'] == 'train'].copy()
test_df = df[df['split'] == 'test'].copy()

y_train = train_df['repeat_ed_within_90d']
y_test = test_df['repeat_ed_within_90d']

base_model = joblib.load(root / "model_artifacts" / "repeat_ed_risk_model.joblib")
if hasattr(base_model, 'feature_names_in_'):
    base_features = list(base_model.feature_names_in_)
else:
    base_features = base_model.named_steps['model'].get_booster().feature_names

selected_features = [
    'acute_cost_velocity_90d',
    'distinct_provider_count_365d',
    'BENE_ESRD_IND'
]
exp_features = base_features + selected_features

X_train_base = train_df[base_features]
X_test_base = test_df[base_features]
X_train_exp = train_df[exp_features]
X_test_exp = test_df[exp_features]

def evaluate(model, X, y, threshold=0.1746):
    probs = model.predict_proba(X)[:, 1]
    preds = (probs >= threshold).astype(int)
    cm = confusion_matrix(y, preds).ravel() # tn, fp, fn, tp
    return {
        'precision': float(precision_score(y, preds, zero_division=0)),
        'recall': float(recall_score(y, preds, zero_division=0)),
        'f1': float(f1_score(y, preds, zero_division=0)),
        'roc_auc': float(roc_auc_score(y, probs)),
        'pr_auc': float(average_precision_score(y, probs)),
        'specificity': float(cm[0] / (cm[0] + cm[1]) if (cm[0]+cm[1])>0 else 0),
        'brier': float(brier_score_loss(y, probs)),
        'cm': {'tn': int(cm[0]), 'fp': int(cm[1]), 'fn': int(cm[2]), 'tp': int(cm[3])},
        'probs': probs
    }

results = {}

# A. Current Production Baseline
print("Running A...")
base_res = evaluate(base_model, X_test_base, y_test)
results['Model_A_Production'] = base_res

# B. Baseline + 3 Features (Current Hyperparams)
print("Running B...")
pipeline_b = Pipeline([
    ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
    ("model", XGBClassifier(
        n_estimators=100, max_depth=4, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8, eval_metric="logloss", random_state=42
    ))
])
pipeline_b.fit(X_train_exp, y_train)
res_b = evaluate(pipeline_b, X_test_exp, y_test)
results['Model_B_CurrentParams_3Feats'] = res_b

# Tuning
print("Tuning...")
tscv = TimeSeriesSplit(n_splits=3)
scorer = make_scorer(average_precision_score, response_method='predict_proba')

param_grid = {
    'model__max_depth': [3, 4, 5, 6],
    'model__learning_rate': [0.05, 0.1, 0.2],
    'model__n_estimators': [100, 200],
    'model__min_child_weight': [1, 3, 5],
    'model__colsample_bytree': [0.6, 0.8, 1.0],
    'model__gamma': [0, 0.5, 1],
    'model__reg_alpha': [0, 0.5, 1],
    'model__reg_lambda': [1, 5, 10]
}

pipeline_base = Pipeline([
    ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
    ("model", XGBClassifier(subsample=0.8, eval_metric="logloss", random_state=42))
])

search_c = RandomizedSearchCV(
    pipeline_base, param_distributions=param_grid, n_iter=20, scoring=scorer,
    cv=tscv, random_state=42, n_jobs=-1
)
search_c.fit(X_train_exp, y_train)

# C. Best Hyperparameter-tuned XGBoost
print("Running C...")
model_c = search_c.best_estimator_
res_c = evaluate(model_c, X_test_exp, y_test)
results['Model_C_Tuned'] = res_c

# Tuning with Class Imbalance
print("Tuning Imbalance...")
pos_weight = (len(y_train) - sum(y_train)) / sum(y_train) # ~10
param_grid_imbalance = param_grid.copy()
param_grid_imbalance['model__scale_pos_weight'] = [2, 5, int(pos_weight)]

search_d = RandomizedSearchCV(
    pipeline_base, param_distributions=param_grid_imbalance, n_iter=20, scoring=scorer,
    cv=tscv, random_state=42, n_jobs=-1
)
search_d.fit(X_train_exp, y_train)

# D. Best Hyperparameter-tuned XGBoost + Class Imbalance Handling
print("Running D...")
model_d = search_d.best_estimator_
res_d = evaluate(model_d, X_test_exp, y_test)
results['Model_D_Tuned_Imbalance'] = res_d

# Feature Importance for best model (C or D depending on PR-AUC, we will save for C)
b_c = model_c.named_steps['model'].get_booster()
imp_c = b_c.get_score(importance_type='gain')
imp_sorted_c = sorted(imp_c.items(), key=lambda x: x[1], reverse=True)

# Save experimental model (Model C)
joblib.dump(model_c, root / "model_artifacts" / "experimental_xgboost_model_v03.joblib")

# Threshold analysis on validation data (train set using OOF or just best model on train for threshold)
probs_train_c = model_c.predict_proba(X_train_exp)[:, 1]
thresholds = [0.10, 0.15, 0.1746, 0.20, 0.25, 0.30]
thresh_res = []
for t in thresholds:
    preds_t = (probs_train_c >= t).astype(int)
    cm_t = confusion_matrix(y_train, preds_t).ravel()
    thresh_res.append({
        'threshold': float(t),
        'precision': float(precision_score(y_train, preds_t, zero_division=0)),
        'recall': float(recall_score(y_train, preds_t, zero_division=0)),
        'f1': float(f1_score(y_train, preds_t, zero_division=0)),
        'specificity': float(cm_t[0] / (cm_t[0] + cm_t[1]) if (cm_t[0]+cm_t[1])>0 else 0),
        'ppr': float((probs_train_c >= t).sum() / len(probs_train_c))
    })

# Overfitting check (Train vs Test PR-AUC)
train_res_c = evaluate(model_c, X_train_exp, y_train)
overfit_gap = float(train_res_c['pr_auc'] - res_c['pr_auc'])

for k in results.keys():
    del results[k]['probs']

report = {
    'metrics': results,
    'cv_results_c': {
        'mean_pr_auc': float(search_c.cv_results_['mean_test_score'][search_c.best_index_]),
        'std_pr_auc': float(search_c.cv_results_['std_test_score'][search_c.best_index_]),
        'best_params': search_c.best_params_
    },
    'cv_results_d': {
        'mean_pr_auc': float(search_d.cv_results_['mean_test_score'][search_d.best_index_]),
        'std_pr_auc': float(search_d.cv_results_['std_test_score'][search_d.best_index_]),
        'best_params': search_d.best_params_
    },
    'importance_c': {k: float(v) for k, v in imp_sorted_c},
    'threshold_analysis': thresh_res,
    'overfit_gap_pr_auc': overfit_gap,
    'train_metrics_c': {
        'pr_auc': train_res_c['pr_auc'],
        'precision': train_res_c['precision'],
        'recall': train_res_c['recall'],
        'f1': train_res_c['f1']
    }
}

with open(root / "tuning_report.json", "w") as f:
    json.dump(report, f, indent=2)

csv_rows = []
for exp_name, res in results.items():
    csv_rows.append({
        'Model': exp_name,
        'Precision': res['precision'],
        'Recall': res['recall'],
        'F1': res['f1'],
        'ROC_AUC': res['roc_auc'],
        'PR_AUC': res['pr_auc'],
        'Specificity': res['specificity'],
        'Brier': res['brier']
    })
pd.DataFrame(csv_rows).to_csv(root / 'UC07_HYPERPARAMETER_RESULTS.csv', index=False)

print("Done.")
