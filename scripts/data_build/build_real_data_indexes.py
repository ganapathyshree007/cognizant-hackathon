import sqlite3
import pandas as pd
import joblib
import sys
import os

def build_patient_db():
    if os.path.exists('patient_features.db'): os.remove('patient_features.db')
    print("Building patient_features.db...")
    conn = sqlite3.connect('patient_features.db')
    
    # 1. Extract exact schema from model
    model = joblib.load('UC07_SYNTHEA_STEP4_BEST_MODEL.joblib')
    features = list(model.feature_names_in_)
    
    # Required keys for provenance
    keys = ['PATIENT_ID', 'ENCOUNTER_ID', 'INDEX_TIMESTAMP']
    
    # Load synthea historical features
    # Use chunking to avoid OOM
    chunksize = 100000
    for chunk in pd.read_csv('UC07_SYNTHEA_STEP4_HISTORICAL_FEATURES.csv', chunksize=chunksize, usecols=keys + features):
        chunk.to_sql('patient_features', conn, if_exists='append', index=False)
        
    # Create indexes for fast lookup
    conn.execute('CREATE INDEX IF NOT EXISTS idx_patient_encounter ON patient_features (PATIENT_ID, ENCOUNTER_ID)')
    conn.commit()
    conn.close()
    print("patient_features.db built successfully.")

def build_provider_db():
    if os.path.exists('provider_index.db'): os.remove('provider_index.db')
    print("Building provider_index.db...")
    conn = sqlite3.connect('provider_index.db')
    
    # Load DAC (Providers)
    print("Loading DAC...")
    for chunk in pd.read_csv('sources/DAC_NationalDownloadableFile.csv', chunksize=100000, low_memory=False, on_bad_lines='skip'):
        # Normalize columns since column names might vary or have spaces
        chunk.columns = [c.strip().lower() for c in chunk.columns]
        
        # Determine actual column names dynamically based on our previous audit
        # NPI, PAC_ID, First Name, Last Name, pri_spec, adr_ln_1, cty, st, zip
        cols_to_keep = {}
        for c in chunk.columns:
            c_low = c.strip().lower()
            if c_low == 'npi': cols_to_keep[c] = 'NPI'
            elif c_low == 'ind_pac_id': cols_to_keep[c] = 'PAC_ID'
            elif c_low == 'provider first name': cols_to_keep[c] = 'First_Name'
            elif c_low == 'provider last name': cols_to_keep[c] = 'Last_Name'
            elif c_low == 'pri_spec': cols_to_keep[c] = 'Specialty'
            
        if not cols_to_keep: continue
        
        df = chunk[list(cols_to_keep.keys())].rename(columns=cols_to_keep)
        
        # Removing dummy LAT/LON assignment as per audit
            
        df.to_sql('dac', conn, if_exists='append', index=False)
        
    print("Loading Facility Affiliations...")
    try:
        for chunk in pd.read_csv('sources/Facility_Affiliations.csv', chunksize=100000, low_memory=False, on_bad_lines='skip'):
            cols_to_keep = {}
            for c in chunk.columns:
                c_low = c.strip().lower()
                if c_low == 'ind_pac_id': cols_to_keep[c] = 'PAC_ID'
                elif c_low == 'facility_id' or c_low == 'ccn' or c_low == 'facility affiliations certification number': cols_to_keep[c] = 'CCN'
            if cols_to_keep:
                df = chunk[list(cols_to_keep.keys())].rename(columns=cols_to_keep)
                df.to_sql('facilities', conn, if_exists='append', index=False)
    except Exception as e:
        print(f"Skipping Facilities: {e}")

    print("Loading Quality Scores...")
    try:
        for chunk in pd.read_csv('sources/ec_score_file.csv', chunksize=100000, low_memory=False, on_bad_lines='skip'):
            cols_to_keep = {}
            for c in chunk.columns:
                c_low = c.strip().lower()
                if c_low == 'npi': cols_to_keep[c] = 'NPI'
                elif c_low == 'final_mips_score': cols_to_keep[c] = 'Quality_Score'
            if cols_to_keep:
                df = chunk[list(cols_to_keep.keys())].rename(columns=cols_to_keep)
                df.to_sql('scores', conn, if_exists='append', index=False)
    except Exception as e:
        print(f"Skipping Scores: {e}")

    print("Loading Utilization...")
    try:
        for chunk in pd.read_csv('sources/Utilization_3.csv', chunksize=100000, low_memory=False, on_bad_lines='skip'):
            cols_to_keep = {}
            for c in chunk.columns:
                c_low = c.strip().lower()
                if c_low == 'npi': cols_to_keep[c] = 'NPI'
                elif c_low == 'procedure_category': cols_to_keep[c] = 'Procedure_Category'
                elif c_low == 'count': cols_to_keep[c] = 'Ordinal_Count'
            if cols_to_keep:
                df = chunk[list(cols_to_keep.keys())].rename(columns=cols_to_keep)
                # Preserve Ordinal_Count as string/object. Drop rows where NPI or Count is null.
                df = df.dropna(subset=['NPI', 'Ordinal_Count'])
                df.to_sql('utilization', conn, if_exists='append', index=False)
    except Exception as e:
        print(f"Skipping Utilization: {e}")

    # Create Indexes
    conn.execute('CREATE INDEX IF NOT EXISTS idx_dac_npi ON dac (NPI)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_dac_pac ON dac (PAC_ID)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_dac_spec ON dac (Specialty)')
    
    # We will query this directly from SQLite using JOINS in the API to save time,
    # or create a materialized view here.
    # To keep provenance clear, the API will run the JOIN dynamically.
    
    conn.commit()
    conn.close()
    print("provider_index.db built successfully.")

if __name__ == "__main__":
    # build_patient_db()
    build_provider_db()
