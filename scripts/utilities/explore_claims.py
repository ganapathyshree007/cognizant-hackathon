import pandas as pd
import json

CMS_DIR = r"c:\COGNIZANT HACKATHON\step 1 2 3"
inp_path = f"{CMS_DIR}\\DE1_0_2008_to_2010_Inpatient_Claims_Sample_1.csv"
out_path = f"{CMS_DIR}\\DE1_0_2008_to_2010_Outpatient_Claims_Sample_1.csv"

def analyze(df, name):
    print(f"--- {name} ---")
    cols = df.columns.tolist()
    print("Columns:", cols)
    
    # non-null percentages
    missing = df.isnull().mean() * 100
    print("Non-null percentages:")
    for c, pct in missing.items():
        if pct < 100:
            print(f"  {c}: {100-pct:.2f}%")
            
    # dtypes
    print("Dtypes:")
    for c in cols[:10]:
        print(f"  {c}: {df[c].dtype}")
        
    print("Rows:", len(df))
    print("Unique CLM_ID:", df['CLM_ID'].nunique())
    
    clm_counts = df['CLM_ID'].value_counts()
    print("CLM_ID distribution:")
    print("  Min rows:", clm_counts.min())
    print("  Max rows:", clm_counts.max())
    print("  Mean rows:", clm_counts.mean())
    print("  Median rows:", clm_counts.median())
    
    multi_claims = clm_counts[clm_counts > 1].index
    if len(multi_claims) > 0:
        print(f"Example multi-row CLM_ID: {multi_claims[0]}")
        samp = df[df['CLM_ID'] == multi_claims[0]]
        print(samp[['CLM_ID', 'DESYNPUF_ID', 'CLM_FROM_DT', 'CLM_THRU_DT', 'PRVDR_NUM', 'CLM_PMT_AMT']].head())
        # Check what is varying
        diff_cols = [c for c in cols if samp[c].nunique(dropna=False) > 1]
        print("Varying columns for this CLM_ID:", diff_cols)
    print("\n")

print("Loading data...")
df_inp = pd.read_csv(inp_path, dtype=str)
df_out = pd.read_csv(out_path, dtype=str)

analyze(df_inp, "Inpatient")
analyze(df_out, "Outpatient")

# check for HCPCS and REV codes
hcpcs_cols_inp = [c for c in df_inp.columns if 'HCPCS' in c]
hcpcs_cols_out = [c for c in df_out.columns if 'HCPCS' in c]
rev_cols_inp = [c for c in df_inp.columns if 'REV' in c]
rev_cols_out = [c for c in df_out.columns if 'REV' in c]

print("Inpatient HCPCS columns:", hcpcs_cols_inp)
print("Outpatient HCPCS columns:", hcpcs_cols_out)
print("Inpatient REV columns:", rev_cols_inp)
print("Outpatient REV columns:", rev_cols_out)

# Check for 99281-99285 in Outpatient HCPCS
ed_cpts = ['99281', '99282', '99283', '99284', '99285']
out_ed_mask = pd.Series([False]*len(df_out))
for c in hcpcs_cols_out:
    out_ed_mask = out_ed_mask | df_out[c].isin(ed_cpts)

print(f"Outpatient rows with ED CPTs: {out_ed_mask.sum()}")
