import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, brier_score_loss, make_scorer
from sklearn.model_selection import TimeSeriesSplit, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier
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

models = {
    'Logistic_Regression': Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler()),
        ('model', LogisticRegression(max_iter=1000, random_state=42, class_weight='balanced')) # baseline balanced since base recall will be 0 at 0.5 without it
    ]),
    'Random_Forest': Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('model', RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, class_weight='balanced'))
    ]),
    'XGBoost': Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('model', XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42, scale_pos_weight=(len(y_train)-y_train.sum())/y_train.sum()))
    ]),
    'LightGBM': Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('model', LGBMClassifier(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42, class_weight='balanced'))
    ]),
    'CatBoost': Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('model', CatBoostClassifier(iterations=100, depth=4, learning_rate=0.1, random_seed=42, auto_class_weights='Balanced', verbose=0))
    ])
}

tscv = TimeSeriesSplit(n_splits=3)
scoring = {
    'pr_auc': make_scorer(average_precision_score, response_method='predict_proba'),
    'roc_auc': make_scorer(roc_auc_score, response_method='predict_proba'),
    'f1': make_scorer(f1_score, zero_division=0),
    'precision': make_scorer(precision_score, zero_division=0),
    'recall': make_scorer(recall_score, zero_division=0)
}

cv_results = {}
final_results = {}

print("Benchmarking models...")
for name, pipeline in models.items():
    print(f"Running {name}...")
    # CV
    cv_res = cross_validate(pipeline, X_train, y_train, cv=tscv, scoring=scoring, n_jobs=-1)
    cv_results[name] = {
        'mean_pr_auc': float(np.mean(cv_res['test_pr_auc'])),
        'std_pr_auc': float(np.std(cv_res['test_pr_auc'])),
        'mean_roc_auc': float(np.mean(cv_res['test_roc_auc'])),
        'std_roc_auc': float(np.std(cv_res['test_roc_auc'])),
        'mean_f1': float(np.mean(cv_res['test_f1'])),
        'std_f1': float(np.std(cv_res['test_f1'])),
        'mean_precision': float(np.mean(cv_res['test_precision'])),
        'mean_recall': float(np.mean(cv_res['test_recall'])),
        'fit_time': float(np.mean(cv_res['fit_time']))
    }
    
    # Final Fit
    pipeline.fit(X_train, y_train)
    joblib.dump(pipeline, root / f"benchmark_{name.lower()}.joblib")
    
    # Final Eval (at threshold 0.5)
    probs = pipeline.predict_proba(X_test)[:, 1]
    preds = (probs >= 0.5).astype(int)
    cm = confusion_matrix(y_test, preds).ravel()
    tn, fp, fn, tp = cm
    
    final_results[name] = {
        'Precision': float(precision_score(y_test, preds, zero_division=0)),
        'Recall': float(recall_score(y_test, preds, zero_division=0)),
        'F1': float(f1_score(y_test, preds, zero_division=0)),
        'PR-AUC': float(average_precision_score(y_test, probs)),
        'ROC-AUC': float(roc_auc_score(y_test, probs)),
        'Specificity': float(tn / (tn + fp) if (tn+fp)>0 else 0),
        'Brier': float(brier_score_loss(y_test, probs)),
        'PPR': float((tp+fp) / len(y_test)),
        'cm': {'tn': int(tn), 'fp': int(fp), 'fn': int(fn), 'tp': int(tp)}
    }
    
    # Feature Importance
    model = pipeline.named_steps['model']
    if name == 'Logistic_Regression':
        importances = np.abs(model.coef_[0])
    elif name == 'CatBoost':
        importances = model.get_feature_importance()
    else:
        importances = model.feature_importances_
        
    feat_imp = sorted(zip(features, importances), key=lambda x: x[1], reverse=True)[:15]
    final_results[name]['top_features'] = {k: float(v) for k, v in feat_imp}

# Save results
with open(root / "benchmark_report.json", "w") as f:
    json.dump({'cv': cv_results, 'final': final_results}, f, indent=2)

csv_rows = []
for name in models.keys():
    row = {'Model': name}
    row.update(final_results[name])
    del row['cm']
    del row['top_features']
    csv_rows.append(row)
pd.DataFrame(csv_rows).to_csv(root / 'UC07_MODEL_BENCHMARK_RESULTS.csv', index=False)

print("Done.")
