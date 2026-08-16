import pandas as pd
from safety_gate_engine import SafetyGateEngine, format_output

def test_synthea_cohort():
    print("=== SYNTHEA COHORT EVALUATION ===\n")
    engine = SafetyGateEngine()
    
    # Load index encounters
    df_idx = pd.read_csv('UC07_SYNTHEA_STEP4_HISTORICAL_FEATURES.csv', usecols=['PATIENT_ID', 'ENCOUNTER_ID', 'INDEX_TIMESTAMP'])
    df_idx['INDEX_TIMESTAMP'] = pd.to_datetime(df_idx['INDEX_TIMESTAMP'], utc=True)
    
    # Load observations to get vitals for these encounters
    df_obs = pd.read_csv('step4_raw/observations.csv', usecols=['DATE', 'ENCOUNTER', 'DESCRIPTION', 'VALUE'])
    df_obs['DATE'] = pd.to_datetime(df_obs['DATE'], utc=True)
    
    # Merge on ENCOUNTER_ID to get same-encounter vitals
    merged = pd.merge(df_idx, df_obs, left_on='ENCOUNTER_ID', right_on='ENCOUNTER')
    # Filter to ensure DATE <= INDEX_TIMESTAMP (triage/before decision point)
    merged = merged[merged['DATE'] <= merged['INDEX_TIMESTAMP']]
    
    rule_counts = {"GREEN": 0, "YELLOW": 0, "RED": 0}
    triggered_rules = set()
    
    encounter_groups = merged.groupby('ENCOUNTER_ID')
    
    for enc_id, group in encounter_groups:
        patient_data = {}
        # Parse vitals
        for _, row in group.iterrows():
            desc = row['DESCRIPTION']
            val = row['VALUE']
            try:
                val = float(val)
                if 'Oxygen' in desc and 'saturation' in desc.lower():
                    patient_data['SpO2'] = val
                elif 'Heart rate' in desc:
                    patient_data['Heart Rate'] = val
                elif 'Respiratory rate' in desc:
                    patient_data['Respiratory Rate'] = val
                elif 'Systolic Blood Pressure' in desc:
                    patient_data['Systolic BP'] = val
                elif 'temperature' in desc.lower():
                    patient_data['Temperature'] = val
                elif 'Pain severity' in desc:
                    patient_data['Pain'] = val
            except:
                pass
                
        # Evaluate
        report = engine.evaluate(patient_data)
        rule_counts[report['Status']] += 1
        if report['Triggered Rule'] != "None":
            triggered_rules.add(report['Triggered Rule'])

    # The missing encounters (no prior vitals) evaluate to GREEN since they have no triggers
    missing_encs = len(df_idx) - len(encounter_groups)
    rule_counts["GREEN"] += missing_encs
    
    print(f"Total Encounters Evaluated: {len(df_idx)}")
    print(f"Status Distribution: {rule_counts}")
    print(f"Rules Actually Triggered by Synthea Data: {sorted(list(triggered_rules))}")
    print("\n")

def test_synthetic_scenarios():
    print("=== SYNTHETIC SCENARIO TESTING ===\n")
    engine = SafetyGateEngine()
    
    scenarios = [
        {
            "name": "Normal Vitals",
            "data": {"SpO2": 98, "Heart Rate": 75, "Respiratory Rate": 16, "Systolic BP": 120, "Temperature": 37.0, "AVPU": "A"}
        },
        {
            "name": "Abnormal SpO2",
            "data": {"SpO2": 88, "Heart Rate": 75, "Respiratory Rate": 16}
        },
        {
            "name": "Severe Chest Pain",
            "data": {"Chest Pain": True, "SpO2": 98, "Heart Rate": 75}
        },
        {
            "name": "Altered Responsiveness",
            "data": {"AVPU": "U", "SpO2": 98, "Heart Rate": 75}
        },
        {
            "name": "Multiple Moderate Abnormalities",
            "data": {"Heart Rate": 135, "Temperature": 39.5, "Pain": 8}
        }
    ]
    
    for sc in scenarios:
        print(f"Scenario: {sc['name']}")
        print("-" * 40)
        report = engine.evaluate(sc['data'])
        print(format_output(report))
        print("=" * 40 + "\n")

if __name__ == "__main__":
    test_synthea_cohort()
    test_synthetic_scenarios()
