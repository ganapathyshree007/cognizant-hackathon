import os
import sys
import json
import pandas as pd
import numpy as np
import joblib
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, confusion_matrix, brier_score_loss

# Add project root to sys path to import backend
os.environ['NAVIGATOR_PROJECT_ROOT'] = r'd:\cognizant-hackathon-main'
sys.path.insert(0, r'd:\cognizant-hackathon-main')
from fastapi.testclient import TestClient

def safe_len(x): return len(x) if x is not None else 0

out = {}

# 1. Inspect Datasets
try:
    df_features = pd.read_csv(r'd:\cognizant-hackathon-main\model_training_data\model_features.csv')
    out['dataset'] = {
        'rows': len(df_features),
        'cols': len(df_features.columns),
        'columns': list(df_features.columns),
        'missing_values': df_features.isnull().sum().to_dict(),
        'duplicates': int(df_features.duplicated().sum()),
        'target_distribution': df_features['repeat_ed_within_90d'].value_counts().to_dict() if 'repeat_ed_within_90d' in df_features.columns else {},
        'split_distribution': df_features['split'].value_counts().to_dict() if 'split' in df_features.columns else {}
    }
except Exception as e:
    out['dataset'] = f"Error reading dataset: {e}"

# 2. Inspect Model
try:
    model_path = r'd:\cognizant-hackathon-main\model_artifacts\repeat_ed_risk_model.joblib'
    model = joblib.load(model_path)
    
    out['model'] = {
        'type': str(type(model)),
    }
    if hasattr(model, 'get_params'):
        out['model']['params'] = {k: str(v) for k, v in model.get_params().items()}
    if hasattr(model, 'feature_names_in_'):
        out['model']['features_expected'] = list(model.feature_names_in_)
    elif hasattr(model, 'get_booster'):
        out['model']['features_expected'] = model.get_booster().feature_names
        
except Exception as e:
    out['model'] = f"Error reading model: {e}"

# 3. Model-Data Compatibility
try:
    expected_features = out['model'].get('features_expected', [])
    actual_features = list(df_features.columns)
    missing_features = [f for f in expected_features if f not in actual_features]
    
    out['compatibility'] = {
        'missing_features': missing_features,
        'pass': len(missing_features) == 0
    }
except Exception as e:
    out['compatibility'] = f"Error: {e}"

# 4. Metrics
try:
    # Use test split if available
    if 'split' in df_features.columns:
        df_test = df_features[df_features['split'] == 'test'].copy()
    else:
        df_test = df_features.copy()
        
    X_test = df_test[expected_features]
    y_test = df_test['repeat_ed_within_90d']
    
    probs = model.predict_proba(X_test)[:, 1]
    threshold = 0.5
    with open(r'd:\cognizant-hackathon-main\model_artifacts\model_report.json', 'r') as f:
        rep = json.load(f)
        threshold = rep.get('selected_operating_threshold', 0.5)
        
    preds = (probs >= threshold).astype(int)
    
    tn, fp, fn, tp = confusion_matrix(y_test, preds).ravel()
    
    out['metrics'] = {
        'threshold': threshold,
        'accuracy': float(accuracy_score(y_test, preds)),
        'precision': float(precision_score(y_test, preds, zero_division=0)),
        'recall': float(recall_score(y_test, preds)),
        'f1': float(f1_score(y_test, preds)),
        'specificity': float(tn / (tn + fp)) if (tn + fp) > 0 else 0,
        'roc_auc': float(roc_auc_score(y_test, probs)),
        'pr_auc': float(average_precision_score(y_test, probs)),
        'brier_score': float(brier_score_loss(y_test, probs)),
        'cm': {'tn': int(tn), 'fp': int(fp), 'fn': int(fn), 'tp': int(tp)}
    }
    
    out['prediction_quality'] = {
        'min_score': float(probs.min()),
        'max_score': float(probs.max()),
        'mean_score': float(probs.mean()),
        'num_positive_preds': int(sum(preds)),
        'num_negative_preds': int(len(preds) - sum(preds))
    }
    
except Exception as e:
    out['metrics'] = f"Error calculating metrics: {e}"

# 5. API vs Direct Model Comparison
try:
    # We must patch backend.main.conn so it doesn't fail if db missing, but wait, we have real data so we can just test the /v1/score endpoint!
    from backend.main import app
    client = TestClient(app)
    
    comparison = []
    # Test top 5 records
    for i in range(min(5, len(df_test))):
        row = df_test.iloc[i]
        features_dict = {f: float(row[f]) if pd.notnull(row[f]) else None for f in expected_features}
        
        # Direct
        x_df = pd.DataFrame([features_dict])
        direct_prob = float(model.predict_proba(x_df)[:, 1])
        direct_band = 'HIGH' if direct_prob >= threshold else 'LOW'
        
        # API
        res = client.post('/v1/score', headers={'x-api-key': 'change-me'}, json={"features": features_dict})
        if res.status_code == 200:
            api_prob = res.json().get('risk_score')
            api_band = res.json().get('risk_band')
            match = (abs(direct_prob - api_prob) < 1e-5) and (direct_band == api_band)
        else:
            api_prob = f"Error: {res.status_code} {res.text}"
            api_band = "Error"
            match = False
            
        comparison.append({
            'record_idx': i,
            'direct_prob': direct_prob,
            'api_prob': api_prob,
            'match': match
        })
    out['api_comparison'] = comparison
except Exception as e:
    out['api_comparison'] = f"Error: {e}"
    import traceback
    out['api_comparison_trace'] = traceback.format_exc()

# 6. Leakage check
try:
    leak_msgs = []
    # If index_date exists, check if any feature like days_since_previous_event is negative
    if 'index_date' in df_features.columns:
        if 'days_since_previous_event' in df_features.columns:
            neg_days = (df_features['days_since_previous_event'] < 0).sum()
            leak_msgs.append(f"Negative days_since_previous_event: {neg_days}")
    out['leakage'] = leak_msgs
except Exception as e:
    out['leakage'] = f"Error: {e}"

with open('eval_output.json', 'w') as f:
    json.dump(out, f, indent=2)
print("Evaluation complete.")
