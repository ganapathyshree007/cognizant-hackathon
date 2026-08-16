import pandas as pd
import numpy as np
from pathlib import Path

root = Path(r"d:\cognizant-hackathon-main")

print("Loading data...")
df = pd.read_csv(root / "model_training_data" / "model_features.csv", parse_dates=["index_date"])
events = pd.read_csv(root / "cleaned_model_inputs" / "claim_events_clean.csv", dtype=str)
events['start_date'] = pd.to_datetime(events['start_date'], errors='coerce')
events['admission_date'] = pd.to_datetime(events['admission_date'], errors='coerce')
events['discharge_date'] = pd.to_datetime(events['discharge_date'], errors='coerce')

events['event_date'] = events['start_date'].dt.normalize()
events['is_inpatient'] = events['encounter_type'].eq('INPATIENT')
events['los'] = (events['discharge_date'] - events['admission_date']).dt.days.fillna(0)

# The bug: df['member_id'] might have different formatting than events['member_id']
# Let's ensure both are strict uppercase stripped strings
df['member_id'] = df['member_id'].astype(str).str.strip().str.upper()
events['member_id'] = events['member_id'].astype(str).str.strip().str.upper()

print("Recalculating...")
histories = {member_id: group for member_id, group in events.groupby('member_id')}

provider_counts = []
recent_los = []

for _, row in df.iterrows():
    m = row['member_id']
    idx_dt = row['index_date']
    if m in histories:
        hist = histories[m]
        mask_365 = (hist['event_date'] >= (idx_dt - pd.Timedelta(days=365))) & (hist['event_date'] < idx_dt)
        prov_count = hist.loc[mask_365, 'provider_npi'].nunique()
        
        mask_inp = hist['is_inpatient'] & (hist['discharge_date'] < idx_dt)
        inp_hist = hist.loc[mask_inp]
        if len(inp_hist) > 0:
            last_stay = inp_hist.loc[inp_hist['discharge_date'].idxmax()]
            los = last_stay['los']
        else:
            los = 0
    else:
        prov_count = 0
        los = 0
        
    provider_counts.append(prov_count)
    recent_los.append(los)

# Load the previously generated exp dataset and just update the two columns
exp_df = pd.read_csv(root / "model_training_data" / "experimental_model_features.csv")
exp_df['distinct_provider_count_365d'] = provider_counts
exp_df['recent_inpatient_los'] = recent_los
exp_df.to_csv(root / "model_training_data" / "experimental_model_features.csv", index=False)
print(f"Fixed sum providers: {sum(provider_counts)}")
print(f"Fixed sum los: {sum(recent_los)}")
