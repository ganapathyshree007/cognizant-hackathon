import pandas as pd
import numpy as np
import os
import glob
import re
import warnings

warnings.filterwarnings('ignore')

RAW_DIR = r"c:\COGNIZANT HACKATHON\step4_raw"
CLEAN_DIR = r"c:\COGNIZANT HACKATHON\step4_cleaned"

os.makedirs(CLEAN_DIR, exist_ok=True)

# 6. Expected Schemas
EXPECTED_COLUMNS = {
    'patients': ['id', 'birthdate', 'deathdate', 'gender', 'race', 'ethnicity', 'marital', 'zip', 'city', 'state', 'healthcare_expenses', 'healthcare_coverage'],
    'encounters': ['id', 'start', 'stop', 'patient', 'encounterclass', 'code', 'description', 'reasoncode', 'reasondescription', 'provider', 'organization'],
    'conditions': ['start', 'stop', 'patient', 'encounter', 'code', 'description'],
    'medications': ['start', 'stop', 'patient', 'encounter', 'code', 'description', 'reasoncode', 'reasondescription'],
    'observations': ['date', 'patient', 'encounter', 'code', 'description', 'value', 'units'],
    'procedures': ['date', 'patient', 'encounter', 'code', 'description', 'reasoncode', 'reasondescription'],
    'careplans': ['id', 'start', 'stop', 'patient', 'encounter', 'code', 'description', 'reasoncode', 'reasondescription'],
    'allergies': ['start', 'stop', 'patient', 'encounter', 'code', 'description'],
    'providers': ['id', 'organization', 'name', 'gender', 'speciality', 'address', 'city', 'state', 'zip', 'lat', 'lon', 'utilization'],
    'organizations': ['id', 'name', 'address', 'city', 'state', 'zip', 'lat', 'lon']
}

def clean_column_name(col):
    c = str(col).strip().lower()
    c = re.sub(r'[^a-z0-9_]', '_', c)
    c = re.sub(r'_+', '_', c)
    return c.strip('_')

def get_base_name(filepath):
    name = os.path.basename(filepath)
    return os.path.splitext(name)[0].lower()

def safe_date_parse(series):
    # try converting to datetime
    parsed = pd.to_datetime(series, errors='coerce')
    invalid_count = parsed.isna().sum() - series.isna().sum() # new NaNs are invalid parses
    # only return formatted date where valid, keep original if invalid
    formatted = parsed.dt.strftime('%Y-%m-%d')
    res = formatted.where(parsed.notna(), series)
    return res, invalid_count

# Discovery
files = glob.glob(os.path.join(RAW_DIR, "*.csv")) + glob.glob(os.path.join(RAW_DIR, "*.xlsx"))

cleaning_log = []
schema_report = []

# Memory for Referential Integrity
keys = {
    'patient': set(),
    'encounter': set(),
    'provider': set(),
    'organization': set()
}

cleaned_dfs = {}
invalid_id_reports = []

print("Starting Synthea Data Cleaning Pipeline...")

for filepath in files:
    filename = os.path.basename(filepath)
    base_name = get_base_name(filepath)
    print(f"\n--- Processing {filename} ---")
    
    try:
        # 2. Read Data Safely (everything as string)
        if filename.endswith('.csv'):
            df = pd.read_csv(filepath, dtype=str)
        else:
            df = pd.read_excel(filepath, dtype=str)
    except Exception as e:
        print(f"ERROR reading {filename}: {e}")
        continue
        
    rows_before, cols_before = df.shape
    print(f"Original: {rows_before} rows, {cols_before} columns")
    print("Original Columns:", df.columns.tolist())
    
    original_cols = df.columns.copy()
    
    # 4. Empty rows and cols
    df_dropped_cols = df.dropna(axis=1, how='all')
    cols_removed = len(df.columns) - len(df_dropped_cols.columns)
    
    df_dropped_rows = df_dropped_cols.dropna(how='all')
    rows_removed = len(df_dropped_cols) - len(df_dropped_rows)
    
    df = df_dropped_rows
    
    # 5. Exact Duplicates
    df_dedup = df.drop_duplicates()
    dups_removed = len(df) - len(df_dedup)
    df = df_dedup
    
    # 3. Column Name Cleaning
    col_map = {c: clean_column_name(c) for c in df.columns}
    df.rename(columns=col_map, inplace=True)
    
    # Track Schema & 10. Missing Value Analysis
    missing_req = []
    additional = []
    if base_name in EXPECTED_COLUMNS:
        expected = EXPECTED_COLUMNS[base_name]
        actual = df.columns.tolist()
        missing_req = [c for c in expected if c not in actual]
        additional = [c for c in actual if c not in expected]
        if missing_req: print(f"Missing required columns: {missing_req}")
        
    # Date detection and categorical stripping
    invalid_dates_total = 0
    date_cols_detected = []
    
    for col in df.columns:
        orig = [k for k,v in col_map.items() if v == col][0]
        
        # 8. Categorical / String trimming
        if df[col].dtype == 'object':
            df[col] = df[col].apply(lambda x: str(x).strip() if pd.notna(x) else x)
            # handle 'nan' strings explicitly if they sneaked in
            df[col] = df[col].replace({'nan': np.nan, 'None': np.nan, '': np.nan})

        # 7. Date Standardization
        if any(d in col for d in ['date', 'start', 'stop']):
            date_cols_detected.append(col)
            df[col], inv = safe_date_parse(df[col])
            invalid_dates_total += inv
            
        missing_count = df[col].isna().sum()
        missing_pct = (missing_count / len(df) * 100) if len(df)>0 else 0
        uniq = df[col].nunique()
        
        # Schema Report
        schema_report.append({
            'dataset': base_name,
            'original_column_name': orig,
            'cleaned_column_name': col,
            'expected_column': 'Yes' if base_name in EXPECTED_COLUMNS and col in EXPECTED_COLUMNS[base_name] else 'No',
            'present': 'Yes',
            'data_type': str(df[col].dtype),
            'missing_count': missing_count,
            'missing_percentage': missing_pct,
            'unique_count': uniq
        })
        
    # 12. ID Validation & Key Collection
    if 'id' in df.columns:
        invalid_ids = df['id'].isna().sum()
        if invalid_ids > 0:
            invalid_id_reports.append(f"{base_name}: {invalid_ids} missing IDs")
        # Collect for RI
        if base_name in keys:
            keys[base_name].update(df['id'].dropna().tolist())

    cleaned_dfs[base_name] = df
    
    # 18. Save output
    out_path = os.path.join(CLEAN_DIR, filename)
    df.to_csv(out_path, index=False)
    
    rows_after, cols_after = df.shape
    
    # 16. Log
    cleaning_log.append({
        'filename': filename,
        'rows_before': rows_before,
        'rows_after': rows_after,
        'columns_before': cols_before,
        'columns_after': cols_after,
        'duplicates_removed': dups_removed,
        'empty_rows_removed': rows_removed,
        'empty_columns_removed': cols_removed,
        'missing_required_columns': "|".join(missing_req),
        'additional_columns': "|".join(additional),
        'date_columns_detected': "|".join(date_cols_detected),
        'invalid_dates': invalid_dates_total,
        'status': 'SUCCESS',
        'warnings': ''
    })
    
# 13. Referential Integrity
print("\nChecking Referential Integrity...")
ri_report = []

def check_ri(child_name, child_col, parent_key_name):
    if child_name in cleaned_dfs:
        df = cleaned_dfs[child_name]
        if child_col in df.columns:
            child_keys = set(df[child_col].dropna().tolist())
            orphans = child_keys - keys[parent_key_name]
            if orphans:
                ri_report.append({'child': child_name, 'column': child_col, 'parent': parent_key_name, 'orphan_count': len(orphans), 'sample_orphans': list(orphans)[:5]})

ri_checks = [
    ('encounters', 'patient', 'patient'),
    ('conditions', 'patient', 'patient'),
    ('conditions', 'encounter', 'encounter'),
    ('medications', 'patient', 'patient'),
    ('medications', 'encounter', 'encounter'),
    ('observations', 'patient', 'patient'),
    ('observations', 'encounter', 'encounter'),
    ('procedures', 'patient', 'patient'),
    ('procedures', 'encounter', 'encounter'),
    ('careplans', 'patient', 'patient'),
    ('careplans', 'encounter', 'encounter'),
    ('allergies', 'patient', 'patient'),
    ('allergies', 'encounter', 'encounter'),
    ('encounters', 'provider', 'provider'),
    ('encounters', 'organization', 'organization'),
    ('providers', 'organization', 'organization')
]

for child, col, parent in ri_checks:
    check_ri(child, col, parent)

# Save logs
pd.DataFrame(cleaning_log).to_csv(os.path.join(CLEAN_DIR, 'cleaning_log.csv'), index=False)
pd.DataFrame(schema_report).to_csv(os.path.join(CLEAN_DIR, 'schema_report.csv'), index=False)
if ri_report:
    pd.DataFrame(ri_report).to_csv(os.path.join(CLEAN_DIR, 'referential_integrity_report.csv'), index=False)
else:
    pd.DataFrame(columns=['child', 'column', 'parent', 'orphan_count', 'sample_orphans']).to_csv(os.path.join(CLEAN_DIR, 'referential_integrity_report.csv'), index=False)

# 22. Final Console Summary
print("\n==================================================")
print("FINAL CONSOLE SUMMARY")
print("==================================================")

log_df = pd.DataFrame(cleaning_log)
if not log_df.empty:
    summary_table = log_df[['filename', 'rows_before', 'rows_after', 'duplicates_removed', 'missing_required_columns', 'date_columns_detected', 'status']]
    print(summary_table.to_string(index=False))
    print("\nStats:")
    print(f"Total datasets processed: {len(log_df)}")
    print(f"Total rows processed: {log_df['rows_before'].sum()}")
    print(f"Total duplicate rows removed: {log_df['duplicates_removed'].sum()}")
    print(f"Output directory: {CLEAN_DIR}")

if ri_report:
    print("\nReferential Integrity Warnings found! Check referential_integrity_report.csv")
else:
    print("\nReferential Integrity: All foreign keys valid.")
    
print("\nPipeline Complete!")
