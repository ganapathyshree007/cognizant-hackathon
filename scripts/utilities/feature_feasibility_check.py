import os
import pandas as pd
import json

out = {}

try:
    events = pd.read_csv(r"d:\cognizant-hackathon-main\cleaned_model_inputs\claim_events_clean.csv", dtype=str, nrows=100000)
    members = pd.read_csv(r"d:\cognizant-hackathon-main\cleaned_model_inputs\member_year_clean.csv", dtype=str, nrows=100000)
    
    # 1. High-risk clinical flags (diagnosis_codes in events)
    out['diagnosis_codes'] = {
        'exists': 'diagnosis_codes' in events.columns,
        'missing_pct': events['diagnosis_codes'].isna().mean() * 100 if 'diagnosis_codes' in events.columns else 100,
        'unique_sample': int(events['diagnosis_codes'].nunique()) if 'diagnosis_codes' in events.columns else 0
    }
    
    # 3. ESRD indicator
    out['BENE_ESRD_IND'] = {
        'exists': 'BENE_ESRD_IND' in members.columns,
        'missing_pct': members['BENE_ESRD_IND'].isna().mean() * 100 if 'BENE_ESRD_IND' in members.columns else 100,
        'unique_values': list(members['BENE_ESRD_IND'].unique()) if 'BENE_ESRD_IND' in members.columns else []
    }
    
    # 4. Length of stay (admission_date, discharge_date)
    out['LOS'] = {
        'admission_exists': 'admission_date' in events.columns,
        'discharge_exists': 'discharge_date' in events.columns,
        'missing_admission': events['admission_date'].isna().mean() * 100 if 'admission_date' in events.columns else 100
    }
    
    # 5. Procedure intensity
    out['procedures'] = {
        'proc_exists': 'procedure_codes' in events.columns,
        'hcpcs_exists': 'hcpcs_codes' in events.columns,
        'proc_missing': events['procedure_codes'].isna().mean() * 100 if 'procedure_codes' in events.columns else 100,
        'hcpcs_missing': events['hcpcs_codes'].isna().mean() * 100 if 'hcpcs_codes' in events.columns else 100
    }
    
    # 6 & 7. Provider and Facility
    out['providers'] = {
        'provider_npi_exists': 'provider_npi' in events.columns,
        'provider_id_exists': 'provider_id' in events.columns, # facility
        'npi_missing': events['provider_npi'].isna().mean() * 100 if 'provider_npi' in events.columns else 100,
        'id_missing': events['provider_id'].isna().mean() * 100 if 'provider_id' in events.columns else 100
    }
    
    # Check current model_features for derived features
    features = pd.read_csv(r"d:\cognizant-hackathon-main\model_training_data\model_features.csv", nrows=100000)
    
    out['derived'] = {
        'ed_365': 'ed_visits_365d' in features.columns,
        'out_365': 'outpatient_visits_365d' in features.columns,
        'paid_30': 'total_paid_30d' in features.columns,
        'paid_90': 'total_paid_90d' in features.columns,
        'ed_30': 'ed_visits_30d' in features.columns,
        'ed_90': 'ed_visits_90d' in features.columns
    }
    
    with open('feature_check.json', 'w') as f:
        json.dump(out, f, indent=2)

except Exception as e:
    with open('feature_check_error.txt', 'w') as f:
        f.write(str(e))
