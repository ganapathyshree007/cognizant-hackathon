import pandas as pd
import json
import os
from collections import defaultdict
import gc

# Base paths
CMS_DIR = r"c:\COGNIZANT HACKATHON\step 1 2 3"
SYN_DIR = r"c:\COGNIZANT HACKATHON\step 4"

CMS_FILES = {
    "Beneficiary_2008": "DE1_0_2008_Beneficiary_Summary_File_Sample_1.csv",
    "Beneficiary_2009": "DE1_0_2009_Beneficiary_Summary_File_Sample_1.csv",
    "Beneficiary_2010": "DE1_0_2010_Beneficiary_Summary_File_Sample_1.csv",
    "Inpatient_Claims": "DE1_0_2008_to_2010_Inpatient_Claims_Sample_1.csv",
    "Outpatient_Claims": "DE1_0_2008_to_2010_Outpatient_Claims_Sample_1.csv"
}

SYN_FILES = [
    "allergies.csv", "careplans.csv", "claims.csv", "conditions.csv", 
    "encounters.csv", "medications.csv", "observations.csv", 
    "organizations.csv", "patients.csv", "procedures.csv", "providers.csv"
]

results = {
    "inventory": {},
    "quality": {},
    "cms_validation": {},
    "synthea_joins": {},
    "cross_join": {},
}

def analyze_file(path, name):
    print(f"Analyzing {name} at {path}")
    df = pd.read_csv(path, low_memory=False)
    
    file_size = os.path.getsize(path)
    rows, cols = df.shape
    columns = list(df.columns)
    dtypes = {c: str(df[c].dtype) for c in df.columns}
    
    # samples
    sample_vals = {c: df[c].dropna().head(3).tolist() for c in columns[:5]} # just first 5 for brevity
    
    # ID column check (heuristic)
    id_cols = [c for c in columns if "ID" in c.upper() or c.upper() == "PATIENT"]
    
    # missing values
    missing = df.isnull().sum().to_dict()
    missing_pct = (df.isnull().sum() / rows * 100).to_dict() if rows > 0 else {}
    
    # distinct counts for IDs
    id_distinct = {c: df[c].nunique() for c in id_cols}
    
    # check blanks for string columns
    blank_counts = {}
    for c in df.select_dtypes(include=['object']):
        blank_counts[c] = int((df[c].astype(str).str.strip() == "").sum())
        
    results["inventory"][name] = {
        "file_size_bytes": file_size,
        "rows": rows,
        "columns": cols,
        "column_names": columns,
        "dtypes": dtypes,
        "sample": sample_vals,
        "id_cols": id_cols
    }
    
    results["quality"][name] = {
        "duplicate_rows": int(df.duplicated().sum()),
        "missing_counts": missing,
        "missing_pct": missing_pct,
        "blank_counts": blank_counts,
        "id_distinct": id_distinct
    }
    
    return df

# Analyze CMS
cms_dfs = {}
for k, v in CMS_FILES.items():
    p = os.path.join(CMS_DIR, v)
    cms_dfs[k] = analyze_file(p, k)
    
# Analyze Synthea
syn_dfs = {}
for f in SYN_FILES:
    name = f.replace(".csv", "")
    p = os.path.join(SYN_DIR, f)
    syn_dfs[name] = analyze_file(p, name)
    
print("Checking CMS Joins")
# Check DESYNPUF_ID overlap between Beneficiary and Claims
bene_ids = set()
for k in ["Beneficiary_2008", "Beneficiary_2009", "Beneficiary_2010"]:
    if "DESYNPUF_ID" in cms_dfs[k].columns:
        bene_ids.update(cms_dfs[k]["DESYNPUF_ID"].dropna().unique())

inpatient_ids = set(cms_dfs["Inpatient_Claims"]["DESYNPUF_ID"].dropna().unique()) if "DESYNPUF_ID" in cms_dfs["Inpatient_Claims"].columns else set()
outpatient_ids = set(cms_dfs["Outpatient_Claims"]["DESYNPUF_ID"].dropna().unique()) if "DESYNPUF_ID" in cms_dfs["Outpatient_Claims"].columns else set()

results["cms_validation"]["join_inpatient"] = {
    "inpatient_total_ids": len(inpatient_ids),
    "in_beneficiary": len(inpatient_ids.intersection(bene_ids)),
    "pct_in_beneficiary": len(inpatient_ids.intersection(bene_ids)) / len(inpatient_ids) * 100 if len(inpatient_ids) > 0 else 0
}
results["cms_validation"]["join_outpatient"] = {
    "outpatient_total_ids": len(outpatient_ids),
    "in_beneficiary": len(outpatient_ids.intersection(bene_ids)),
    "pct_in_beneficiary": len(outpatient_ids.intersection(bene_ids)) / len(outpatient_ids) * 100 if len(outpatient_ids) > 0 else 0
}

# Check CLM_ID uniqueness
clm_ids_inp = cms_dfs["Inpatient_Claims"]["CLM_ID"] if "CLM_ID" in cms_dfs["Inpatient_Claims"].columns else pd.Series()
clm_ids_outp = cms_dfs["Outpatient_Claims"]["CLM_ID"] if "CLM_ID" in cms_dfs["Outpatient_Claims"].columns else pd.Series()
results["cms_validation"]["clm_id_unique_inpatient"] = clm_ids_inp.is_unique
results["cms_validation"]["clm_id_unique_outpatient"] = clm_ids_outp.is_unique
# Intersection of clm_ids
intersect_clm = set(clm_ids_inp).intersection(set(clm_ids_outp))
results["cms_validation"]["clm_ids_overlap_count"] = len(intersect_clm)


print("Checking Synthea Joins")
# Synthea relations
relations = [
    ("patients", "Id", "encounters", "PATIENT"),
    ("patients", "Id", "conditions", "PATIENT"),
    ("patients", "Id", "observations", "PATIENT"),
    ("patients", "Id", "medications", "PATIENT"),
    ("patients", "Id", "procedures", "PATIENT"),
    ("patients", "Id", "careplans", "PATIENT"),
    ("patients", "Id", "claims", "PATIENT"),
    ("providers", "Id", "encounters", "PROVIDER"),
    ("organizations", "Id", "providers", "ORGANIZATION")
]

for parent, p_col, child, c_col in relations:
    if parent in syn_dfs and child in syn_dfs and p_col in syn_dfs[parent].columns and c_col in syn_dfs[child].columns:
        p_keys = set(syn_dfs[parent][p_col].dropna().unique())
        c_keys = set(syn_dfs[child][c_col].dropna().unique())
        c_total = len(syn_dfs[child])
        c_matched = syn_dfs[child][c_col].isin(p_keys).sum()
        
        results["synthea_joins"][f"{parent}_{child}"] = {
            "parent": parent,
            "child": child,
            "join_col": c_col,
            "parent_unique": len(p_keys),
            "child_total_records": int(c_total),
            "child_match_records": int(c_matched),
            "match_rate": float(c_matched / c_total * 100) if c_total > 0 else 0
        }

print("Checking Cross Dataset Joins")
# Cross-dataset join
syn_patient_ids = set(syn_dfs["patients"]["Id"].dropna().unique()) if "patients" in syn_dfs and "Id" in syn_dfs["patients"].columns else set()
overlap = bene_ids.intersection(syn_patient_ids)
results["cross_join"]["overlap_count"] = len(overlap)

with open(r"c:\COGNIZANT HACKATHON\audit_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("Done. Results saved to audit_results.json")
