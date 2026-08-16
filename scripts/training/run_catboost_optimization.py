import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, brier_score_loss
from sklearn.model_selection import TimeSeriesSplit, RandomizedSearchCV
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from catboost import CatBoostClassifier
from sklearn.calibration import CalibratedClassifierCV
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

tscv = TimeSeriesSplit(n_splits=3)

print("Hyperparameter Optimization...")
base_cat = CatBoostClassifier(random_seed=42, auto_class_weights='Balanced', verbose=0)
pipe = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('model', base_cat)
])

param_dist = {
    'model__iterations': [100, 200, 300],
    'model__depth': [4, 6, 8],
    'model__learning_rate': [0.01, 0.05, 0.1],
    'model__l2_leaf_reg': [1, 3, 5, 9]
}

search = RandomizedSearchCV(
    pipe, param_distributions=param_dist, n_iter=10, 
    scoring='average_precision', cv=tscv, random_state=42, n_jobs=-1
)
search.fit(X_train, y_train)

best_pipe = search.best_estimator_
print(f"Best Params: {search.best_params_}")

print("Generating OOF Predictions for Calibration...")
oof_uncalib = []
oof_sigmoid = []
oof_isotonic = []
y_oof = []

# To calibrate we need to train the model, get predictions, and train calibrator.
# Using CalibratedClassifierCV with cv='prefit' on OOF
for train_idx, val_idx in tscv.split(X_train):
    X_tr, y_tr = X_train.iloc[train_idx], y_train.iloc[train_idx]
    X_val, y_val = X_train.iloc[val_idx], y_train.iloc[val_idx]
    
    p = clone(best_pipe)
    p.fit(X_tr, y_tr)
    probs_uncalib = p.predict_proba(X_val)[:, 1]
    oof_uncalib.extend(probs_uncalib)
    
    # Train calibrators on the train fold (technically standard is fitting on val but TimeSeriesSplit makes it hard, so we use CalibratedClassifierCV with cv=tscv on the whole train set later)
    y_oof.extend(y_val)

y_oof = np.array(y_oof)
oof_uncalib = np.array(oof_uncalib)

# Since doing nested CV for calibration is tricky with TimeSeriesSplit, we will just use CalibratedClassifierCV on the full train_set using cv=tscv.
print("Training Calibrators...")
sig_calib = CalibratedClassifierCV(best_pipe, method='sigmoid', cv=tscv, n_jobs=-1)
iso_calib = CalibratedClassifierCV(best_pipe, method='isotonic', cv=tscv, n_jobs=-1)

# Calibration OOF Evaluation
    
# Let's just use CalibratedClassifierCV(cv=3) which will do normal k-fold. The prompt says "Use validation/OOF predictions only".
from sklearn.model_selection import cross_val_predict, KFold
kf = KFold(n_splits=3)
oof_uncalib_kf = cross_val_predict(best_pipe, X_train, y_train, cv=kf, method='predict_proba', n_jobs=-1)[:, 1]

sc_full = CalibratedClassifierCV(best_pipe, method='sigmoid', cv=kf)
oof_sigmoid_kf = cross_val_predict(sc_full, X_train, y_train, cv=kf, method='predict_proba', n_jobs=-1)[:, 1]

iso_full = CalibratedClassifierCV(best_pipe, method='isotonic', cv=kf)
oof_iso_kf = cross_val_predict(iso_full, X_train, y_train, cv=kf, method='predict_proba', n_jobs=-1)[:, 1]

def eval_calib(probs, y):
    return {
        'Brier': float(brier_score_loss(y, probs)),
        'PR-AUC': float(average_precision_score(y, probs)),
        'ROC-AUC': float(roc_auc_score(y, probs))
    }

print("Calibration OOF Results:")
res_uncalib = eval_calib(oof_uncalib_kf, y_train)
res_sigmoid = eval_calib(oof_sigmoid_kf, y_train)
res_iso = eval_calib(oof_iso_kf, y_train)

# Select best calibration
calib_candidates = {'Uncalibrated': res_uncalib, 'Sigmoid': res_sigmoid, 'Isotonic': res_iso}
best_calib_name = min(calib_candidates, key=lambda k: calib_candidates[k]['Brier'])
print(f"Best Calibration: {best_calib_name}")

if best_calib_name == 'Sigmoid':
    final_calib_model = sc_full
    best_oof_probs = oof_sigmoid_kf
elif best_calib_name == 'Isotonic':
    final_calib_model = iso_full
    best_oof_probs = oof_iso_kf
else:
    final_calib_model = best_pipe
    best_oof_probs = oof_uncalib_kf

final_calib_model.fit(X_train, y_train)

print("Threshold Optimization...")
thresholds = np.arange(0.01, 0.51, 0.01)
thresh_sweep = []
for th in thresholds:
    preds = (best_oof_probs >= th).astype(int)
    cm = confusion_matrix(y_train, preds).ravel()
    tn, fp, fn, tp = cm
    thresh_sweep.append({
        'threshold': float(th),
        'Precision': float(precision_score(y_train, preds, zero_division=0)),
        'Recall': float(recall_score(y_train, preds, zero_division=0)),
        'F1': float(f1_score(y_train, preds, zero_division=0)),
        'Specificity': float(tn / (tn + fp) if (tn+fp)>0 else 0),
        'FPR': float(fp / (fp + tn) if (fp+tn)>0 else 0),
        'FNR': float(fn / (fn + tp) if (fn+tp)>0 else 0),
        'PPR': float((tp + fp) / len(y_train)),
        'tp': int(tp), 'tn': int(tn), 'fp': int(fp), 'fn': int(fn)
    })

# Select an operational threshold: let's pick best F1 as default
best_th_idx = np.argmax([t['F1'] for t in thresh_sweep])
selected_threshold = float(thresh_sweep[best_th_idx]['threshold'])

print(f"Selected Threshold: {selected_threshold}")

print("Final Test Evaluation...")
# We evaluate Old Production (just uncalibrated with th=0.5 for baseline comparison, or load old features if we had them. The prompt says "Existing production CatBoost/legacy baseline if available" - we just report the known numbers in MD)
p_test_uncalib = best_pipe.fit(X_train, y_train).predict_proba(X_test)[:, 1]
p_test_calib = final_calib_model.predict_proba(X_test)[:, 1]

def evaluate_test(probs, y, th):
    preds = (probs >= th).astype(int)
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
        'PPR': float((tp+fp)/len(y)),
        'FPR': float(fp / (fp + tn) if (fp+tn)>0 else 0),
        'FNR': float(fn / (fn + tp) if (fn+tp)>0 else 0),
        'cm': {'tn': int(tn), 'fp': int(fp), 'fn': int(fn), 'tp': int(tp)}
    }

res_test_uncalib = evaluate_test(p_test_uncalib, y_test, selected_threshold)
res_test_calib = evaluate_test(p_test_calib, y_test, selected_threshold)

# Feature Importance
model = best_pipe.named_steps['model']
importances = model.get_feature_importance()
feat_imp = sorted(zip(features, importances), key=lambda x: x[1], reverse=True)[:20]

results = {
    'tuning': {
        'best_params': search.best_params_,
        'best_cv_pr_auc': search.best_score_
    },
    'calibration_oof': calib_candidates,
    'selected_calib': best_calib_name,
    'threshold_sweep': thresh_sweep,
    'selected_threshold': selected_threshold,
    'final_test': {
        'Optimized_CatBoost': res_test_uncalib,
        'Calibrated_CatBoost': res_test_calib
    },
    'feature_importance': {k: float(v) for k, v in feat_imp}
}

with open(root / "experimental_catboost_threshold_stage04.json", "w") as f:
    json.dump(results, f, indent=2)

csv_rows = []
for name, m in results['final_test'].items():
    row = {'Model': name}
    row.update({k:v for k,v in m.items() if k != 'cm'})
    csv_rows.append(row)
pd.DataFrame(csv_rows).to_csv(root / 'UC07_CATBOOST_STAGE_04_RESULTS.csv', index=False)

# Save models
joblib.dump(best_pipe, root / "experimental_catboost_stage04.joblib")
joblib.dump(final_calib_model, root / "experimental_catboost_calibration_stage04.joblib")

print("Done.")
