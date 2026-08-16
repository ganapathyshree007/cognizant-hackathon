import joblib
import pandas as pd
import numpy as np

def main():
    model_path = 'UC07_SYNTHEA_STEP4_BEST_MODEL.joblib'
    print(f"Loading {model_path}...")
    model = joblib.load(model_path)
    
    # Check what type of object it is
    print(f"Type: {type(model)}")
    
    # Try to extract feature names if possible
    features = []
    if hasattr(model, 'feature_name_'):
        features = model.feature_name_
        print("Found feature_name_")
    elif hasattr(model, 'feature_names_in_'):
        features = list(model.feature_names_in_)
        print("Found feature_names_in_")
    else:
        print("No explicit feature names array found in model object.")
    
    # Load 1 row of data
    df = pd.read_csv('UC07_final_40_features.csv', nrows=2)
    
    # If features were found, filter the dataframe to only those features
    if features:
        # Check if features match dataframe columns
        missing = [f for f in features if f not in df.columns]
        if missing:
            print(f"Missing features in CSV: {missing}")
        else:
            X = df[features].iloc[[0]]
            try:
                preds = model.predict_proba(X)
                print(f"Prediction success! Probabilities: {preds}")
            except Exception as e:
                print(f"Prediction failed: {e}")
    else:
        # Try to predict on the whole row (minus ID/target if present)
        cols_to_drop = ['PATIENT_ID', 'ENCOUNTER_ID', 'INDEX_DATE', 'TARGET_REPEAT_ED_90D']
        X = df.drop(columns=[c for c in cols_to_drop if c in df.columns], errors='ignore')
        try:
            preds = model.predict_proba(X.iloc[[0]])
            print(f"Prediction success on arbitrary columns! Probabilities: {preds}")
        except Exception as e:
            print(f"Prediction failed on arbitrary columns: {e}")

if __name__ == "__main__":
    main()
