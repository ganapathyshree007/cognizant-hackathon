# UC07 Step 4: Synthea Historical Risk Feature Build Report

## Cohort Summary
- **Total Index Rows**: 2061
- **Total Unique Patients**: 803
- **Positive Count**: 381
- **Negative Count**: 1680
- **Positive Prevalence**: 18.49%

## Target Definition
`repeat_ed_90d = 1` if another ED encounter starts strictly after the index ED date (not on the same calendar day) and within 90 days.

## Exclusions Handled
- **Same-Day ED Encounters**: Collapsed to the first encounter of the calendar day. Subsequent ED events on the same day are ignored for targets.
- **Death**: Patients who died strictly within 90 days without a repeat ED were excluded.
- **Insufficient Follow-up**: Index events within 90 days of the dataset's maximum date (`observation_end_date`) were excluded.

## Feature Summary (44 features)
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
- QUALITY: Zero/low variance in state. Uniques = 1
