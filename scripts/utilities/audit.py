import pandas as pd
import os
import json

DATA_DIR = r"D:\cognizant-hackathon-main\step4_raw"
FILES = [
    "patients.csv", "encounters.csv", "conditions.csv", "medications.csv",
    "observations.csv", "procedures.csv", "careplans.csv", "allergies.csv",
    "claims.csv", "providers.csv", "organizations.csv"
]

results = {}

def get_identifier(cols, possible_names):
    for c in cols:
        if c.lower() in possible_names:
            return c
    return None

def analyze_table(file_path):
    df = pd.read_csv(file_path)
    cols = df.columns.tolist()
    
    # Identify key columns
    pid = get_identifier(cols, ["patient", "pat_id", "patient_id"])
    eid = get_identifier(cols, ["encounter", "enc_id", "encounter_id"])
    pid_primary = get_identifier(cols, ["id"]) # usually id in patients, organizations, providers, encounters
    
    # Identify date columns
    date_cols = [c for c in cols if 'date' in c.lower() or 'start' in c.lower() or 'end' in c.lower() or 'time' in c.lower()]
    
    # Important clinical cols
    clinical_cols = [c for c in cols if 'code' in c.lower() or 'description' in c.lower() or 'reason' in c.lower() or 'value' in c.lower()]
    
    # Date range
    date_range = {}
    for dc in date_cols:
        try:
            # fast parsing
            parsed = pd.to_datetime(df[dc].dropna(), format='mixed', errors='coerce')
            valid = parsed.dropna()
            if not valid.empty:
                date_range[dc] = [valid.min().strftime('%Y-%m-%d'), valid.max().strftime('%Y-%m-%d')]
        except:
            pass

    # Missingness
    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(2).to_dict()
    
    primary_id = None
    if pid_primary:
        primary_id = pid_primary
    elif 'Id' in cols:
        primary_id = 'Id'
        
    return {
        "filename": os.path.basename(file_path),
        "row_count": len(df),
        "column_count": len(cols),
        "columns": cols,
        "primary_identifier": primary_id,
        "patient_identifier": pid,
        "encounter_identifier": eid,
        "date_columns": date_cols,
        "important_clinical_columns": clinical_cols,
        "missingness": missing_pct,
        "duplicate_counts": df.duplicated().sum(),
        "date_range": date_range
    }

for f in FILES:
    path = os.path.join(DATA_DIR, f)
    if os.path.exists(path):
        results[f] = analyze_table(path)

print("--- FILE INVENTORY ---")
for f, data in results.items():
    print(f"File: {data['filename']}")
    print(f"Row count: {data['row_count']}, Col count: {data['column_count']}")
    print(f"Duplicate rows: {data['duplicate_counts']}")
    print(f"Patient ID: {data['patient_identifier']}, Encounter ID: {data['encounter_identifier']}")
    print(f"Date ranges: {data['date_range']}")
    print("---")

# 2. VALIDATE MY FRIEND'S EXISTING APPROACH
print("--- VALIDATION ---")
patients = pd.read_csv(os.path.join(DATA_DIR, "patients.csv"))
encounters = pd.read_csv(os.path.join(DATA_DIR, "encounters.csv"))

print(f"Raw Patients: {len(patients)}")
print(f"Raw Encounters: {len(encounters)}")

# Synthea encounter class for ED is typically "emergency"
print("Encounter classes available:", encounters['ENCOUNTERCLASS'].unique())

ed_encounters = encounters[encounters['ENCOUNTERCLASS'].str.lower() == 'emergency'].copy()
print(f"Raw Emergency Encounters: {len(ed_encounters)}")

# Sort by patient and start date
ed_encounters['START_DATE'] = pd.to_datetime(ed_encounters['START'], format='mixed', errors='coerce').dt.tz_localize(None)
ed_encounters = ed_encounters.sort_values(by=['PATIENT', 'START_DATE'])

# Exclusions
# Need to check deaths. Deaths are in patients.csv
patients['DEATHDATE'] = pd.to_datetime(patients['DEATHDATE'], format='mixed', errors='coerce').dt.tz_localize(None)
deaths = patients.dropna(subset=['DEATHDATE'])[['Id', 'DEATHDATE']].rename(columns={'Id': 'PATIENT'})

ed_with_deaths = pd.merge(ed_encounters, deaths, on='PATIENT', how='left')

# Exclude final 90-day follow-up. 
# Max date in encounters?
max_date = pd.to_datetime(encounters['START'], format='mixed', errors='coerce').dt.tz_localize(None).max()
cutoff_date = max_date - pd.Timedelta(days=90)
print(f"Dataset Max Date: {max_date}")
print(f"90-day cutoff: {cutoff_date}")

# 41 excluded from final 90-day follow-up
excluded_followup = ed_encounters[ed_encounters['START_DATE'] > cutoff_date]
print(f"Excluded from final 90-day follow-up (> {cutoff_date}): {len(excluded_followup)}")

# 72 excluded because death occurred within the target window
# Condition: deathdate is between index date and index date + 90 days
ed_with_deaths['within_90d'] = (ed_with_deaths['DEATHDATE'] > ed_with_deaths['START_DATE']) & (ed_with_deaths['DEATHDATE'] <= ed_with_deaths['START_DATE'] + pd.Timedelta(days=90))
excluded_deaths = ed_with_deaths[ed_with_deaths['within_90d']]
print(f"Excluded because death occurred within 90 days: {len(excluded_deaths)}")

# Target definition checks
print("Target definition analysis...")
same_day = ed_encounters.groupby(['PATIENT', ed_encounters['START_DATE'].dt.date]).size()
print(f"Multiple ED encounters on same date (count of patient-dates > 1): {(same_day > 1).sum()}")

# To construct the actual positive cases
valid_ed = ed_with_deaths[ed_with_deaths['START_DATE'] <= cutoff_date]
valid_ed = valid_ed[~valid_ed['within_90d']]
print(f"Final ED index rows: {len(valid_ed)}")

# Check target positives
valid_ed['repeat_ed_90d'] = 0
valid_ed['days_to_next_ed'] = valid_ed.groupby('PATIENT')['START_DATE'].diff(periods=-1).dt.days * -1
valid_ed.loc[(valid_ed['days_to_next_ed'] > 0) & (valid_ed['days_to_next_ed'] <= 90), 'repeat_ed_90d'] = 1
print(f"Positives (repeat_ed_90d == 1): {valid_ed['repeat_ed_90d'].sum()}")

# Friend's test set: 87 index rows, 71 patients, 16 positives. 
# Total dataset numbers we have...
print(f"Total positive cases in entire dataset: {valid_ed['repeat_ed_90d'].sum()}")
print(f"Total index rows: {len(valid_ed)}")
print(f"Total unique patients in index rows: {valid_ed['PATIENT'].nunique()}")

