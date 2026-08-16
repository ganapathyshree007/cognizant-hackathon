import os
import sys
import json
import pandas as pd
import numpy as np
import joblib
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, confusion_matrix, brier_score_loss

try:
    df = pd.read_csv(r'd:\cognizant-hackathon-main\model_training_data\model_features.csv')
    model = joblib.load(r'd:\cognizant-hackathon-main\model_artifacts\repeat_ed_risk_model.joblib')
    
    out = {}
    
    expected_features = []
    if hasattr(model, 'feature_names_in_'):
        expected_features = list(model.feature_names_in_)
    else:
        # It's a pipeline
        booster = model.named_steps['model'].get_booster()
        expected_features = booster.feature_names
        
    df_test = df[df['split'] == 'test'].copy()
    X_test = df_test[expected_features]
    y_test = df_test['repeat_ed_within_90d']
    
    probs = model.predict_proba(X_test)[:, 1]
    
    # Target
    out['target'] = {
        'column': 'repeat_ed_within_90d',
        'positives': int(y_test.sum()),
        'negatives': int(len(y_test) - y_test.sum()),
        'total': int(len(y_test))
    }
    
    # Thresholds
    thresholds = [0.1, 0.1746, 0.2, 0.3, 0.4, 0.5]
    out['thresholds'] = {}
    for t in thresholds:
        preds = (probs >= t).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_test, preds).ravel()
        out['thresholds'][str(t)] = {
            'precision': float(precision_score(y_test, preds, zero_division=0)),
            'recall': float(recall_score(y_test, preds)),
            'f1': float(f1_score(y_test, preds)),
            'cm': {'tn': int(tn), 'fp': int(fp), 'fn': int(fn), 'tp': int(tp)}
        }
    
    # Feature Importance
    b = model.named_steps['model'].get_booster()
    importance = b.get_score(importance_type='gain')
    imp_sorted = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    out['importance'] = {k: float(v) for k, v in imp_sorted}
    
    # Prediction distribution
    out['distribution'] = {
        'min': float(probs.min()),
        'max': float(probs.max()),
        'mean': float(probs.mean()),
        'median': float(np.median(probs)),
        'p90': float(np.percentile(probs, 90)),
        'p99': float(np.percentile(probs, 99)),
        'above_05': int((probs > 0.5).sum()),
        'above_threshold': int((probs >= 0.1746).sum())
    }
    
    # Error Analysis (sample indices)
    preds = (probs >= 0.1746).astype(int)
    fp_idx = df_test.iloc[np.where((preds == 1) & (y_test == 0))[0]]
    fn_idx = df_test.iloc[np.where((preds == 0) & (y_test == 1))[0]]
    
    # average values for fp vs fn to understand why they failed
    out['errors'] = {
        'fp_mean_age': float(fp_idx['age_at_year_end'].mean()),
        'fp_mean_ed_90d': float(fp_idx['ed_visits_90d'].mean()),
        'fp_mean_inpatient_90d': float(fp_idx['inpatient_visits_90d'].mean()),
        
        'fn_mean_age': float(fn_idx['age_at_year_end'].mean()),
        'fn_mean_ed_90d': float(fn_idx['ed_visits_90d'].mean()),
        'fn_mean_inpatient_90d': float(fn_idx['inpatient_visits_90d'].mean())
    }
    
    # Feature quality
    out['feature_quality'] = {}
    for f in expected_features:
        col = df[f]
        out['feature_quality'][f] = {
            'missing': int(col.isnull().sum()),
            'unique': int(col.nunique()),
            'variance': float(col.var()) if pd.api.types.is_numeric_dtype(col) else 0.0
        }
        
    with open('diagnostic_output.json', 'w') as f:
        json.dump(out, f, indent=2)

except Exception as e:
    with open('diagnostic_error.txt', 'w') as f:
        f.write(str(e))
