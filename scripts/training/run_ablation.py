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
df = pd.read_csv(root / "model_training_data" / "experimental_model_features.csv")
train_df = df[df['split'] == 'train']
test_df = df[df['split'] == 'test']

y_train = train_df['repeat_ed_within_90d']
y_test = test_df['repeat_ed_within_90d']

base_model = joblib.load(root / "model_artifacts" / "repeat_ed_risk_model.joblib")
if hasattr(base_model, 'feature_names_in_'):
    base_features = list(base_model.feature_names_in_)
else:
    base_features = base_model.named_steps['model'].get_booster().feature_names

features_to_test = {
    'A_ESRD': 'BENE_ESRD_IND',
    'B_Provider': 'distinct_provider_count_365d',
    'C_ED_Out_Ratio': 'ed_to_outpatient_ratio_365d',
    'D_Cost_Vel': 'acute_cost_velocity_90d',
    'E_LOS': 'recent_inpatient_los'
}

def build_model():
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
        ("model", XGBClassifier(
            n_estimators=100, max_depth=4, learning_rate=0.1,
            subsample=0.8, colsample_bytree=0.8, eval_metric="logloss", random_state=42
        ))
    ])

def evaluate(model, X, y, threshold=0.1746):
    probs = model.predict_proba(X)[:, 1]
    preds = (probs >= threshold).astype(int)
    cm = confusion_matrix(y, preds).ravel() # tn, fp, fn, tp
    return {
        'precision': precision_score(y, preds, zero_division=0),
        'recall': recall_score(y, preds, zero_division=0),
        'f1': f1_score(y, preds, zero_division=0),
        'roc_auc': roc_auc_score(y, probs),
        'pr_auc': average_precision_score(y, probs),
        'specificity': cm[0] / (cm[0] + cm[1]) if (cm[0]+cm[1])>0 else 0,
        'brier': brier_score_loss(y, probs),
        'cm': {'tn': int(cm[0]), 'fp': int(cm[1]), 'fn': int(cm[2]), 'tp': int(cm[3])},
        'probs': probs
    }

results = {}
feature_importances = {}
prediction_distributions = {}

def run_experiment(name, features):
    print(f"Running {name}...")
    X_train = train_df[features]
    X_test = test_df[features]
    
    pipeline = build_model()
    pipeline.fit(X_train, y_train)
    
    res = evaluate(pipeline, X_test, y_test)
    
    # Feature importance
    b = pipeline.named_steps['model'].get_booster()
    imp = b.get_score(importance_type='gain')
    imp_sorted = sorted(imp.items(), key=lambda x: x[1], reverse=True)
    imp_dict = {k: float(v) for k, v in imp_sorted}
    feature_importances[name] = imp_dict
    
    # Prediction distribution
    probs = res['probs']
    prediction_distributions[name] = {
        'min': float(np.min(probs)),
        'max': float(np.max(probs)),
        'mean': float(np.mean(probs)),
        'median': float(np.median(probs)),
        'p25': float(np.percentile(probs, 25)),
        'p75': float(np.percentile(probs, 75)),
        'above_threshold': int((probs >= 0.1746).sum()),
        'ppr': float((probs >= 0.1746).sum() / len(probs))
    }
    
    del res['probs']
    results[name] = res
    return res

# 1. Baseline
run_experiment('Baseline', base_features)

# 2. Individual Ablations
for name, f in features_to_test.items():
    run_experiment(name, base_features + [f])

# 3. Choose Best Combination
best_f1_feature = None
best_f1 = results['Baseline']['f1']
second_best_feature = None
second_best_f1 = results['Baseline']['f1']

# Simple ranking based on F1
improvements = []
for name, f in features_to_test.items():
    if results[name]['f1'] >= results['Baseline']['f1']:
        improvements.append((name, f, results[name]['f1']))

improvements.sort(key=lambda x: x[2], reverse=True)

if len(improvements) > 0:
    best_name, best_f, _ = improvements[0]
    if len(improvements) > 1:
        sec_name, sec_f, _ = improvements[1]
        run_experiment('Comb_Top2', base_features + [best_f, sec_f])
    if len(improvements) > 2:
        third_name, third_f, _ = improvements[2]
        run_experiment('Comb_Top3', base_features + [best_f, sec_f, third_f])
else:
    # No feature improved F1, maybe pick the one that improved PR-AUC or Recall most
    print("No individual feature improved F1.")

# Create UC07_FEATURE_ABLATION_RESULTS.csv
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

pd.DataFrame(csv_rows).to_csv(root / 'UC07_FEATURE_ABLATION_RESULTS.csv', index=False)

# Save JSON report
with open(root / 'ablation_report.json', 'w') as f:
    json.dump({
        'metrics': results,
        'importance': feature_importances,
        'distributions': prediction_distributions
    }, f, indent=2)

print("Done.")
