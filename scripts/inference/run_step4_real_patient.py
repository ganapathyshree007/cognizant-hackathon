import joblib
import pandas as pd
import numpy as np
import argparse
import sys

def predict_patient(model, expected_features, row, is_print=True):
    # Extract only the 44 expected features
    X = pd.DataFrame([row[expected_features]])
    
    # Predict
    prob = model.predict_proba(X)[0][1]
    
    # Determine band and class
    risk_band = "LOW"
    if prob > 0.6:
        risk_band = "HIGH"
    elif prob > 0.3:
        risk_band = "MEDIUM"
        
    predicted_class = 1 if prob >= 0.5 else 0  # Assuming standard 0.5 threshold for class, but band is the clinical outcome
    
    if is_print:
        print("========================================")
        print("UC07 STEP 4 REAL PATIENT PREDICTION")
        print("========================================")
        print(f"Patient ID: {row['PATIENT_ID']}")
        if 'ENCOUNTER_ID' in row:
            print(f"Encounter ID: {row['ENCOUNTER_ID']}")
        if 'INDEX_TIMESTAMP' in row:
            print(f"Index Timestamp: {row['INDEX_TIMESTAMP']}")
        
        print("\nModel:\nUC07_SYNTHEA_STEP4_BEST_MODEL.joblib")
        print("\nInput source:\nUC07_SYNTHEA_STEP4_HISTORICAL_FEATURES.csv")
        print(f"\nFeatures used: {len(expected_features)}")
        print(f"\nHistorical Repeat-ED Probability: {prob:.4f}")
        print(f"Risk Band: {risk_band}")
        print(f"Prediction: {risk_band} RISK")
        print("========================================")
        print(f"Actual Target in Dataset: {row.get('target_repeat_ed_90d', 'UNKNOWN')}")
        print("========================================")
        
    return {
        'patient_id': row['PATIENT_ID'],
        'index_timestamp': row.get('INDEX_TIMESTAMP', ''),
        'predicted_probability': round(prob, 4),
        'predicted_class': predicted_class,
        'risk_band': risk_band,
        'actual_target': row.get('target_repeat_ed_90d', -1)
    }

def main():
    parser = argparse.ArgumentParser(description="Test Step 4 Model on Real Patients")
    parser.add_argument("--patient-id", type=str, help="Run prediction for a specific Patient ID")
    parser.add_argument("--all", action="store_true", help="Run prediction for all patients in dataset")
    args = parser.parse_args()

    print("Loading model and dataset...")
    try:
        model = joblib.load("UC07_SYNTHEA_STEP4_BEST_MODEL.joblib")
        df = pd.read_csv("UC07_SYNTHEA_STEP4_HISTORICAL_FEATURES.csv")
    except Exception as e:
        print(f"Error loading files: {e}")
        sys.exit(1)

    expected_features = list(getattr(model, "feature_names_in_", []))
    
    if not expected_features:
        print("Could not extract feature_names_in_ from model. Is it a Pipeline wrapper?")
        # Attempt to dig into Pipeline or CalibratedClassifierCV
        if hasattr(model, 'estimator'):
            expected_features = list(getattr(model.estimator, "feature_names_in_", []))
        if hasattr(model, 'calibrated_classifiers_'):
            est = model.calibrated_classifiers_[0].estimator
            expected_features = list(getattr(est, "feature_names_in_", []))
            
    if not expected_features:
        # Fallback based on known 44 features
        expected_features = [c for c in df.columns if c not in ['PATIENT_ID', 'ENCOUNTER_ID', 'INDEX_TIMESTAMP', 'target_repeat_ed_90d']]
        
    # Verify features
    print(f"Feature count expected by model: {len(expected_features)}")
    missing = set(expected_features) - set(df.columns)
    if missing:
        print(f"CRITICAL ERROR: Features expected by model are missing in dataset: {missing}")
        sys.exit(1)
        
    if len(expected_features) != 44:
        print(f"WARNING: Expected exactly 44 features, found {len(expected_features)}.")

    if args.all:
        print(f"Running inference on all {len(df)} rows...")
        results = []
        for idx, row in df.iterrows():
            res = predict_patient(model, expected_features, row, is_print=False)
            results.append(res)
        
        res_df = pd.DataFrame(results)
        res_df.to_csv("UC07_STEP4_REAL_INFERENCE_RESULTS.csv", index=False)
        print("Exported results to UC07_STEP4_REAL_INFERENCE_RESULTS.csv")
        sys.exit(0)
        
    elif args.patient_id:
        pat_id = args.patient_id
    else:
        # Interactive mode
        sample_patients = df['PATIENT_ID'].sample(5, random_state=42).tolist()
        print("\nAvailable Sample Patient IDs:")
        for p in sample_patients:
            print(f"- {p}")
        pat_id = input("\nEnter a PATIENT_ID to evaluate: ").strip()

    patient_rows = df[df['PATIENT_ID'] == pat_id]
    if patient_rows.empty:
        print(f"Error: Patient ID {pat_id} not found in dataset.")
        sys.exit(1)
        
    # Run prediction on the most recent row for this patient
    patient_row = patient_rows.sort_values(by='INDEX_TIMESTAMP', ascending=False).iloc[0]
    predict_patient(model, expected_features, patient_row, is_print=True)

if __name__ == "__main__":
    main()
