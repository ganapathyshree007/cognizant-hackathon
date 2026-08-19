import os
import sys
import joblib
import pandas as pd
import sqlite3

# 1. Check Model Artifact
model_path = os.path.abspath('models/UC07_SYNTHEA_STEP4_BEST_MODEL.joblib')
print(f"MODEL ARTIFACT: {os.path.basename(model_path)}")
print(f"MODEL LOADING LOCATION: {model_path}")

model = joblib.load(model_path)
print(f"MODEL TYPE: {type(model)}")

features = model.feature_names_in_
print(f"FEATURE COUNT: {len(features)}")
print(f"FEATURES: {list(features)[:5]} ...")

# 2. Get some real data to score
conn = sqlite3.connect('data/patient_features.db')
df = pd.read_sql_query("SELECT * FROM patient_features LIMIT 1", conn)
conn.close()

if df.empty:
    print("No data found to test.")
    sys.exit(1)

X = df[features]
prob = model.predict_proba(X)[0][1]

if prob > 0.15: risk_band = 'HIGH'
elif prob > 0.05: risk_band = 'MEDIUM'
else: risk_band = 'LOW'

print(f"PREDICTION METHOD: predict_proba")
print(f"OUTPUT (Probability): {prob}")
print(f"RISK BAND: {risk_band}")
