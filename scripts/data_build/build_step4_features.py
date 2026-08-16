import pandas as pd
import numpy as np
import os
from datetime import timedelta

DATA_DIR = r"D:\cognizant-hackathon-main\step4_raw"

def load_data():
    print("Loading datasets...")
    patients = pd.read_csv(os.path.join(DATA_DIR, "patients.csv"))
    encounters = pd.read_csv(os.path.join(DATA_DIR, "encounters.csv"))
    conditions = pd.read_csv(os.path.join(DATA_DIR, "conditions.csv"))
    medications = pd.read_csv(os.path.join(DATA_DIR, "medications.csv"))
    procedures = pd.read_csv(os.path.join(DATA_DIR, "procedures.csv"))
    careplans = pd.read_csv(os.path.join(DATA_DIR, "careplans.csv"))
    
    # Process dates
    for df in [encounters, conditions, medications, procedures, careplans]:
        if 'START' in df.columns:
            df['START'] = pd.to_datetime(df['START'], format='mixed', errors='coerce').dt.tz_localize(None)
        if 'STOP' in df.columns:
            df['STOP'] = pd.to_datetime(df['STOP'], format='mixed', errors='coerce').dt.tz_localize(None)
    
    patients['BIRTHDATE'] = pd.to_datetime(patients['BIRTHDATE'], format='mixed', errors='coerce').dt.tz_localize(None)
    patients['DEATHDATE'] = pd.to_datetime(patients['DEATHDATE'], format='mixed', errors='coerce').dt.tz_localize(None)
    
    return patients, encounters, conditions, medications, procedures, careplans

def build_index_cohort(encounters, patients):
    print("Building index cohort...")
    ed = encounters[encounters['ENCOUNTERCLASS'].str.lower() == 'emergency'].copy()
    ed = ed.sort_values(by=['PATIENT', 'START'])
    
    # Same calendar day collapse: Keep first ED encounter per patient per day
    ed['START_DATE_ONLY'] = ed['START'].dt.date
    ed['is_first_of_day'] = ~ed.duplicated(subset=['PATIENT', 'START_DATE_ONLY'], keep='first')
    
    index_candidates = ed[ed['is_first_of_day']].copy()
    
    # Global Max Date for insufficient follow up
    observation_end_date = encounters['START'].max()
    print(f"Global observation end date: {observation_end_date}")
    
    results = []
    
    for _, row in index_candidates.iterrows():
        pat_id = row['PATIENT']
        index_ts = row['START']
        index_date = row['START_DATE_ONLY']
        enc_id = row['Id']
        
        # Check target: next ED encounter
        # Must be strictly > index_ts AND > index_date (not on the same day)
        patient_ed = ed[ed['PATIENT'] == pat_id]
        future_ed = patient_ed[(patient_ed['START_DATE_ONLY'] > index_date) & 
                               (patient_ed['START'] <= index_ts + timedelta(days=90))]
        
        target = 1 if len(future_ed) > 0 else 0
        
        # Determine exclusions
        exclude = False
        reason = ""
        
        pat_info = patients[patients['Id'] == pat_id]
        death_date = pat_info['DEATHDATE'].values[0] if not pat_info.empty else np.datetime64('NaT')
        
        # Insufficient follow up
        if index_ts + timedelta(days=90) > observation_end_date:
            exclude = True
            reason = "Insufficient follow up"
            
        # Death within 90 days
        if not exclude and not pd.isna(death_date):
            death_date_ts = pd.to_datetime(death_date)
            if death_date_ts <= index_ts + timedelta(days=90):
                # Die within 90 days. If target=1 (had ED before dying), we keep. Otherwise exclude.
                if target == 0:
                    exclude = True
                    reason = "Death within 90 days without repeat ED"

        if not exclude:
            results.append({
                'PATIENT_ID': pat_id,
                'ENCOUNTER_ID': enc_id,
                'INDEX_TIMESTAMP': index_ts,
                'target_repeat_ed_90d': target
            })
            
    df_index = pd.DataFrame(results)
    return df_index

def extract_features(df_index, patients, encounters, conditions, medications, procedures, careplans):
    print("Extracting features...")
    feature_rows = []
    
    for i, row in df_index.iterrows():
        if i % 500 == 0:
            print(f"Processed {i}/{len(df_index)}")
        
        pat = row['PATIENT_ID']
        idx_ts = row['INDEX_TIMESTAMP']
        
        # Demographics
        p_info = patients[patients['Id'] == pat].iloc[0]
        age = (idx_ts - p_info['BIRTHDATE']).days / 365.25 if not pd.isna(p_info['BIRTHDATE']) else np.nan
        
        feat = {
            'PATIENT_ID': pat,
            'ENCOUNTER_ID': row['ENCOUNTER_ID'],
            'INDEX_TIMESTAMP': idx_ts,
            'target_repeat_ed_90d': row['target_repeat_ed_90d'],
            'age_at_index': age,
            'gender': p_info.get('GENDER', ''),
            'race': p_info.get('RACE', ''),
            'ethnicity': p_info.get('ETHNICITY', ''),
            'marital_status': p_info.get('MARITAL', ''),
            'state': p_info.get('STATE', '')
        }
        
        # -----------------------------
        # STRICT POINT IN TIME FILTERING
        # -----------------------------
        p_enc = encounters[(encounters['PATIENT'] == pat) & (encounters['START'] < idx_ts)]
        p_cond = conditions[(conditions['PATIENT'] == pat) & (conditions['START'] < idx_ts)]
        p_med = medications[(medications['PATIENT'] == pat) & (medications['START'] < idx_ts)]
        p_proc = procedures[(procedures['PATIENT'] == pat) & (procedures['START'] < idx_ts)]
        p_care = careplans[(careplans['PATIENT'] == pat) & (careplans['START'] < idx_ts)]
        
        # Utilization (30/90/365d)
        for days in [30, 90, 365]:
            limit = idx_ts - timedelta(days=days)
            enc_period = p_enc[p_enc['START'] >= limit]
            
            feat[f'all_encounters_{days}d'] = len(enc_period)
            feat[f'emergency_{days}d'] = len(enc_period[enc_period['ENCOUNTERCLASS'].str.lower() == 'emergency'])
            feat[f'inpatient_{days}d'] = len(enc_period[enc_period['ENCOUNTERCLASS'].str.lower() == 'inpatient'])
            feat[f'outpatient_{days}d'] = len(enc_period[enc_period['ENCOUNTERCLASS'].str.lower() == 'outpatient'])
            feat[f'ambulatory_{days}d'] = len(enc_period[enc_period['ENCOUNTERCLASS'].str.lower() == 'ambulatory'])
            feat[f'urgent_care_{days}d'] = len(enc_period[enc_period['ENCOUNTERCLASS'].str.lower() == 'urgentcare'])
            feat[f'wellness_{days}d'] = len(enc_period[enc_period['ENCOUNTERCLASS'].str.lower() == 'wellness'])
            
            feat[f'total_encounter_cost_{days}d'] = enc_period['BASE_ENCOUNTER_COST'].sum() if 'BASE_ENCOUNTER_COST' in enc_period else 0
            
        # Recency
        if not p_enc.empty:
            feat['days_since_previous_encounter'] = (idx_ts - p_enc['START'].max()).days
        else:
            feat['days_since_previous_encounter'] = 9999
            
        ed_past = p_enc[p_enc['ENCOUNTERCLASS'].str.lower() == 'emergency']
        feat['days_since_previous_ed'] = (idx_ts - ed_past['START'].max()).days if not ed_past.empty else 9999
        
        inp_past = p_enc[p_enc['ENCOUNTERCLASS'].str.lower() == 'inpatient']
        feat['days_since_last_inpatient'] = (idx_ts - inp_past['START'].max()).days if not inp_past.empty else 9999
        
        outp_past = p_enc[p_enc['ENCOUNTERCLASS'].str.lower() == 'outpatient']
        feat['days_since_last_outpatient'] = (idx_ts - outp_past['START'].max()).days if not outp_past.empty else 9999

        # Conditions
        feat['hist_condition_count'] = len(p_cond)
        feat['hist_unique_condition_count'] = p_cond['CODE'].nunique() if not p_cond.empty else 0
        active_cond = p_cond[pd.isna(p_cond['STOP']) | (p_cond['STOP'] >= idx_ts)]
        feat['hist_active_condition_count'] = len(active_cond)
        
        # For chronic, Synthea doesn't explicitly flag. Let's proxy chronic by active condition length > 1 year or just active count.
        # We will use active_condition_count as the robust measure.
        feat['hist_chronic_condition_count'] = len(active_cond[active_cond['START'] <= idx_ts - timedelta(days=365)])
        
        # Medications
        feat['hist_medication_count'] = len(p_med)
        feat['hist_medication_diversity'] = p_med['CODE'].nunique() if not p_med.empty else 0
        active_med = p_med[pd.isna(p_med['STOP']) | (p_med['STOP'] >= idx_ts)]
        feat['hist_active_medication_count'] = len(active_med)
        
        # Procedures
        feat['hist_procedure_count'] = len(p_proc)
        feat['hist_unique_procedure_count'] = p_proc['CODE'].nunique() if not p_proc.empty else 0
        
        # Careplans
        feat['hist_careplan_count'] = len(p_care)

        feature_rows.append(feat)
        
    return pd.DataFrame(feature_rows)

def data_quality_and_leakage_audit(df):
    print("Running Data Quality & Leakage Audit...")
    report = []
    failed = False
    
    # 1. Identifier Check
    ml_features = [c for c in df.columns if c not in ['PATIENT_ID', 'ENCOUNTER_ID', 'INDEX_TIMESTAMP', 'target_repeat_ed_90d']]
    
    for id_col in ['id', 'patient', 'encounter', 'uuid']:
        for c in ml_features:
            c_lower = c.lower()
            if c_lower == id_col or c_lower.endswith('_id') or c_lower.endswith('id'):
                # Avoid false positive on 'invalid' or something if it happens, but simple ends_with is safer
                if c_lower not in ['days_since_previous_ed']: # ED doesn't end with id but 'ed'
                    failed = True
                    report.append(f"LEAKAGE: Potential ID column found in ML features: {c}")

    # 2. Future Information Check
    recency_cols = [c for c in ml_features if 'days_since' in c]
    for c in recency_cols:
        if (df[c] < 0).any():
            failed = True
            report.append(f"LEAKAGE: Negative value in {c}. Future event leaked!")

    # 3. Missingness and Zero variance
    missing = df[ml_features].isnull().sum() / len(df) * 100
    for c in ml_features:
        if missing[c] > 50:
            report.append(f"QUALITY: High missingness in {c}: {missing[c]:.1f}%")
        if df[c].nunique() <= 1:
            report.append(f"QUALITY: Zero/low variance in {c}. Uniques = {df[c].nunique()}")
            
    if failed:
        print("AUDIT FAILED! See report.")
        for r in report: print(r)
        raise ValueError("Leakage or critical quality failure detected.")
    
    print("Audit passed successfully.")
    return report

def generate_markdown_report(df, dq_report, out_path):
    ml_features = [c for c in df.columns if c not in ['PATIENT_ID', 'ENCOUNTER_ID', 'INDEX_TIMESTAMP', 'target_repeat_ed_90d']]
    
    md = f"""# UC07 Step 4: Synthea Historical Risk Feature Build Report

## Cohort Summary
- **Total Index Rows**: {len(df)}
- **Total Unique Patients**: {df['PATIENT_ID'].nunique()}
- **Positive Count**: {df['target_repeat_ed_90d'].sum()}
- **Negative Count**: {len(df) - df['target_repeat_ed_90d'].sum()}
- **Positive Prevalence**: {df['target_repeat_ed_90d'].mean()*100:.2f}%

## Target Definition
`repeat_ed_90d = 1` if another ED encounter starts strictly after the index ED date (not on the same calendar day) and within 90 days.

## Exclusions Handled
- **Same-Day ED Encounters**: Collapsed to the first encounter of the calendar day. Subsequent ED events on the same day are ignored for targets.
- **Death**: Patients who died strictly within 90 days without a repeat ED were excluded.
- **Insufficient Follow-up**: Index events within 90 days of the dataset's maximum date (`observation_end_date`) were excluded.

## Feature Summary ({len(ml_features)} features)
### Demographics
`age_at_index`, `gender`, `race`, `ethnicity`, `marital_status`, `state`

### Recency
`days_since_previous_encounter`, `days_since_previous_ed`, `days_since_last_inpatient`, `days_since_last_outpatient`

### Utilization (30/90/365d)
`all_encounters`, `emergency`, `inpatient`, `outpatient`, `ambulatory`, `urgent_care`, `wellness`

### Cost (30/90/365d)
`total_encounter_cost`

### Clinical
- **Conditions**: `hist_condition_count`, `hist_unique_condition_count`, `hist_active_condition_count`, `hist_chronic_condition_count`
- **Medications**: `hist_medication_count`, `hist_active_medication_count`, `hist_medication_diversity`
- **Procedures**: `hist_procedure_count`, `hist_unique_procedure_count`
- **Careplans**: `hist_careplan_count`

## Leakage Audit
- Strict temporal boundary `event_timestamp < INDEX_TIMESTAMP` was applied.
- Excluded Patient/Encounter IDs from the ML feature matrix.
- Recency fields verified strictly >= 0.
- **Status: PASSED**

## Data Quality Warnings
"""
    for r in dq_report:
        md += f"- {r}\n"
        
    with open(out_path, 'w') as f:
        f.write(md)

def main():
    patients, encounters, conditions, medications, procedures, careplans = load_data()
    
    df_index = build_index_cohort(encounters, patients)
    
    df_features = extract_features(df_index, patients, encounters, conditions, medications, procedures, careplans)
    
    dq_report = data_quality_and_leakage_audit(df_features)
    
    # Save datasets
    df_features.to_csv("UC07_SYNTHEA_STEP4_HISTORICAL_FEATURES.csv", index=False)
    generate_markdown_report(df_features, dq_report, "UC07_SYNTHEA_STEP4_FEATURE_BUILD_REPORT.md")
    print("Done. Exported UC07_SYNTHEA_STEP4_HISTORICAL_FEATURES.csv and UC07_SYNTHEA_STEP4_FEATURE_BUILD_REPORT.md")

if __name__ == "__main__":
    main()
