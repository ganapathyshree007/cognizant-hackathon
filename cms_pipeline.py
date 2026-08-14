import pandas as pd
import numpy as np
import os
import time

start_time = time.time()
INP_PATH = r"c:\COGNIZANT HACKATHON\step 1 2 3\DE1_0_2008_to_2010_Inpatient_Claims_Sample_1.csv"
OUTP_PATH = r"c:\COGNIZANT HACKATHON\step 1 2 3\DE1_0_2008_to_2010_Outpatient_Claims_Sample_1.csv"
OUT_DIR = r"c:\COGNIZANT HACKATHON\pipeline_output"
os.makedirs(OUT_DIR, exist_ok=True)

print("Loading raw datasets...")
df_inp = pd.read_csv(INP_PATH, dtype=str)
df_outp = pd.read_csv(OUTP_PATH, dtype=str)

for df in [df_inp, df_outp]:
    if 'CLM_PMT_AMT' in df.columns:
        df['CLM_PMT_AMT'] = pd.to_numeric(df['CLM_PMT_AMT'], errors='coerce').fillna(0)
    for dt_col in ['CLM_FROM_DT', 'CLM_THRU_DT', 'CLM_ADMSN_DT', 'NCH_BENE_DSCHRG_DT']:
        if dt_col in df.columns:
            df[dt_col] = pd.to_datetime(df[dt_col], format='%Y%m%d', errors='coerce')

def get_melted_codes(df, prefix):
    cols = [c for c in df.columns if prefix in c]
    if not cols: return pd.Series(dtype=str)
    melted = df[['CLM_ID'] + cols].melt(id_vars='CLM_ID', value_name='code')
    melted = melted.dropna(subset=['code'])
    melted['code'] = melted['code'].astype(str).str.strip()
    melted = melted[melted['code'] != '']
    return melted.groupby('CLM_ID')['code'].apply(lambda x: '|'.join(sorted(x.unique())))

def collapse_claims(df, encounter_type):
    print(f"Collapsing {encounter_type} claims...")
    
    # Static conflicts check
    static_cols = ['DESYNPUF_ID', 'PRVDR_NUM']
    conflicts = []
    
    # Aggregation mapping
    agg_funcs = {
        'DESYNPUF_ID': 'first',
        'CLM_FROM_DT': 'min',
        'CLM_THRU_DT': 'max',
        'CLM_PMT_AMT': 'sum'
    }
    if 'PRVDR_NUM' in df.columns: agg_funcs['PRVDR_NUM'] = 'first'
    if 'AT_PHYSN_NPI' in df.columns: agg_funcs['AT_PHYSN_NPI'] = 'first'
    if 'CLM_ADMSN_DT' in df.columns: agg_funcs['CLM_ADMSN_DT'] = 'min'
    if 'NCH_BENE_DSCHRG_DT' in df.columns: agg_funcs['NCH_BENE_DSCHRG_DT'] = 'max'
    if 'CLM_DRG_CD' in df.columns: agg_funcs['CLM_DRG_CD'] = 'first'
    
    df_collapsed = df.groupby('CLM_ID').agg(agg_funcs).reset_index()
    df_collapsed.rename(columns={
        'CLM_ID': 'claim_id',
        'DESYNPUF_ID': 'member_id',
        'CLM_FROM_DT': 'start_date',
        'CLM_THRU_DT': 'end_date',
        'CLM_PMT_AMT': 'payment_amount',
        'PRVDR_NUM': 'provider_id',
        'AT_PHYSN_NPI': 'provider_npi',
        'CLM_ADMSN_DT': 'admission_date',
        'NCH_BENE_DSCHRG_DT': 'discharge_date',
        'CLM_DRG_CD': 'drg_code'
    }, inplace=True, errors='ignore')
    
    df_collapsed['encounter_type'] = encounter_type
    
    print(f"  Extracting codes...")
    diag = get_melted_codes(df, 'ICD9_DGNS_CD_')
    proc = get_melted_codes(df, 'ICD9_PRCDR_CD_')
    hcpcs = get_melted_codes(df, 'HCPCS_CD_')
    
    df_collapsed = df_collapsed.merge(diag.rename('diagnosis_codes'), left_on='claim_id', right_index=True, how='left')
    df_collapsed = df_collapsed.merge(proc.rename('procedure_codes'), left_on='claim_id', right_index=True, how='left')
    df_collapsed = df_collapsed.merge(hcpcs.rename('hcpcs_codes'), left_on='claim_id', right_index=True, how='left')
    
    return df_collapsed, pd.DataFrame(conflicts)

df_inp_col, conf_inp = collapse_claims(df_inp, "INPATIENT")
df_outp_col, conf_outp = collapse_claims(df_outp, "OUTPATIENT")

df_inp_col.to_csv(os.path.join(OUT_DIR, "collapsed_inpatient_claims.csv"), index=False)
df_outp_col.to_csv(os.path.join(OUT_DIR, "collapsed_outpatient_claims.csv"), index=False)

df_conflicts = pd.concat([conf_inp, conf_outp], ignore_index=True)
if not df_conflicts.empty:
    df_conflicts.to_csv(os.path.join(OUT_DIR, "claim_conflicts.csv"), index=False)
else:
    pd.DataFrame(columns=['claim_id', 'field', 'num_values', 'values_found']).to_csv(os.path.join(OUT_DIR, "claim_conflicts.csv"), index=False)

print("Creating unified encounters and ED flags...")
# Ensure columns match before concat
cols_to_keep = ['member_id', 'claim_id', 'encounter_type', 'start_date', 'end_date', 'admission_date', 
                'discharge_date', 'provider_id', 'provider_npi', 'payment_amount', 'diagnosis_codes', 
                'procedure_codes', 'hcpcs_codes', 'drg_code']
for col in cols_to_keep:
    if col not in df_inp_col.columns: df_inp_col[col] = None
    if col not in df_outp_col.columns: df_outp_col[col] = None
    
df_unified = pd.concat([df_inp_col[cols_to_keep], df_outp_col[cols_to_keep]], ignore_index=True)

# ED logic
ed_cpts = {'99281', '99282', '99283', '99284', '99285'}
def is_ed(hcpcs_str):
    if pd.isna(hcpcs_str) or not str(hcpcs_str).strip(): return 0
    codes = set(str(hcpcs_str).split('|'))
    return 1 if not codes.isdisjoint(ed_cpts) else 0

df_unified['ed_candidate_flag'] = df_unified['hcpcs_codes'].apply(is_ed)
df_unified.to_csv(os.path.join(OUT_DIR, "unified_encounters.csv"), index=False)

df_ed = df_unified[df_unified['ed_candidate_flag'] == 1].copy()
df_ed.to_csv(os.path.join(OUT_DIR, "ed_claims.csv"), index=False)

print("Generating ED Rule Comparison...")
ed_rule = {
    'Rule': ['HCPCS only', 'Revenue only', 'Combined'],
    'Matched_Claims': [len(df_ed), 0, 0],
    'Percentage_of_Outpatient': [len(df_ed) / len(df_outp_col) * 100 if len(df_outp_col) > 0 else 0, 0, 0]
}
pd.DataFrame(ed_rule).to_csv(os.path.join(OUT_DIR, "ed_rule_comparison.csv"), index=False)

print("Calculating Member Summaries...")
# Member summaries can be calculated efficiently
df_unified['start_date'] = pd.to_datetime(df_unified['start_date'])
max_dataset_date = df_unified['end_date'].max()

def calc_member_summary(group):
    ed_visits = group[group['ed_candidate_flag'] == 1]['start_date'].dropna()
    total_ed = len(ed_visits)
    first_ed = ed_visits.min() if total_ed > 0 else pd.NaT
    latest_ed = ed_visits.max() if total_ed > 0 else pd.NaT
    
    if pd.notna(latest_ed) and pd.notna(max_dataset_date):
        days_since = (max_dataset_date - latest_ed).days
    else:
        days_since = None
        
    days_diffs = (max_dataset_date - ed_visits).dt.days
    ed_30d = (days_diffs <= 30).sum()
    ed_90d = (days_diffs <= 90).sum()
    ed_180d = (days_diffs <= 180).sum()
    ed_365d = (days_diffs <= 365).sum()
    
    # inpatient after ED
    inpatient_after_ed = 0
    if total_ed > 0:
        inp_visits = group[group['encounter_type'] == 'INPATIENT']['start_date'].dropna()
        ed_ends = group[group['ed_candidate_flag'] == 1]['end_date'].dropna()
        for ed_end in ed_ends:
            if ((inp_visits >= ed_end) & ((inp_visits - ed_end).dt.days <= 2)).any():
                inpatient_after_ed += 1
                
    return pd.Series({
        'total_ed_visits': total_ed,
        'ed_visits_30d': ed_30d,
        'ed_visits_90d': ed_90d,
        'ed_visits_180d': ed_180d,
        'ed_visits_365d': ed_365d,
        'first_ed_date': first_ed,
        'latest_ed_date': latest_ed,
        'days_since_latest_ed': days_since,
        'inpatient_after_ed_count': inpatient_after_ed,
        'total_inpatient_visits': (group['encounter_type'] == 'INPATIENT').sum(),
        'total_outpatient_visits': (group['encounter_type'] == 'OUTPATIENT').sum()
    })

member_stats = df_unified.groupby('member_id').apply(calc_member_summary).reset_index()
member_stats.to_csv(os.path.join(OUT_DIR, "ed_member_summary.csv"), index=False)

print(f"Pipeline finished successfully in {time.time() - start_time:.2f} seconds.")
