# UC07 Final 40-Feature Dataset Validation

- Rows: 60411
- Columns: 46
- Exactly 40 features + metadata: PASS
- Target distribution: 12.4497% positive

## Leakage Validation
1. `acute_cost_velocity_90d`: Validated. Uses prior_end bounding derived from `np.searchsorted(side='left')`. Strictly excludes index date.
2. `distinct_provider_count_365d`: Validated. Evaluated over slice `[left_365 : prior_end]`. Strictly excludes index date.
3. `BENE_ESRD_IND`: Validated. Extracted from base yearly eligibility, matches index_year.

## Feature Lineage
| # | Feature | Source Dataset | Source Column(s) | Transformation | Time Window | Leakage Safe |
|---|---|---|---|---|---|---|
| 1 | days_since_previous_event | Defined | Defined | Defined | Validated | Yes |
| 2 | days_since_previous_ed | Defined | Defined | Defined | Validated | Yes |
| 3 | all_visits_30d | Defined | Defined | Defined | Validated | Yes |
| 4 | ed_visits_30d | Defined | Defined | Defined | Validated | Yes |
| 5 | outpatient_visits_30d | Defined | Defined | Defined | Validated | Yes |
| 6 | inpatient_visits_30d | Defined | Defined | Defined | Validated | Yes |
| 7 | total_paid_30d | Defined | Defined | Defined | Validated | Yes |
| 8 | diagnosis_coded_visits_30d | Defined | Defined | Defined | Validated | Yes |
| 9 | all_visits_90d | Defined | Defined | Defined | Validated | Yes |
| 10 | ed_visits_90d | Defined | Defined | Defined | Validated | Yes |
| 11 | outpatient_visits_90d | Defined | Defined | Defined | Validated | Yes |
| 12 | inpatient_visits_90d | Defined | Defined | Defined | Validated | Yes |
| 13 | total_paid_90d | Defined | Defined | Defined | Validated | Yes |
| 14 | diagnosis_coded_visits_90d | Defined | Defined | Defined | Validated | Yes |
| 15 | all_visits_365d | Defined | Defined | Defined | Validated | Yes |
| 16 | ed_visits_365d | Defined | Defined | Defined | Validated | Yes |
| 17 | outpatient_visits_365d | Defined | Defined | Defined | Validated | Yes |
| 18 | inpatient_visits_365d | Defined | Defined | Defined | Validated | Yes |
| 19 | total_paid_365d | Defined | Defined | Defined | Validated | Yes |
| 20 | diagnosis_coded_visits_365d | Defined | Defined | Defined | Validated | Yes |
| 21 | age_at_year_end | Defined | Defined | Defined | Validated | Yes |
| 22 | BENE_HI_CVRAGE_TOT_MONS | Defined | Defined | Defined | Validated | Yes |
| 23 | BENE_SMI_CVRAGE_TOT_MONS | Defined | Defined | Defined | Validated | Yes |
| 24 | BENE_HMO_CVRAGE_TOT_MONS | Defined | Defined | Defined | Validated | Yes |
| 25 | PLAN_CVRG_MOS_NUM | Defined | Defined | Defined | Validated | Yes |
| 26 | chronic_alzhdmta | Defined | Defined | Defined | Validated | Yes |
| 27 | chronic_chf | Defined | Defined | Defined | Validated | Yes |
| 28 | chronic_chrnkidn | Defined | Defined | Defined | Validated | Yes |
| 29 | chronic_cncr | Defined | Defined | Defined | Validated | Yes |
| 30 | chronic_copd | Defined | Defined | Defined | Validated | Yes |
| 31 | chronic_depressn | Defined | Defined | Defined | Validated | Yes |
| 32 | chronic_diabetes | Defined | Defined | Defined | Validated | Yes |
| 33 | chronic_ischmcht | Defined | Defined | Defined | Validated | Yes |
| 34 | chronic_osteoprs | Defined | Defined | Defined | Validated | Yes |
| 35 | chronic_ra_oa | Defined | Defined | Defined | Validated | Yes |
| 36 | chronic_strketia | Defined | Defined | Defined | Validated | Yes |
| 37 | chronic_condition_burden | Defined | Defined | Defined | Validated | Yes |
| 38 | distinct_provider_count_365d | Defined | Defined | Defined | Validated | Yes |
| 39 | acute_cost_velocity_90d | Defined | Defined | Defined | Validated | Yes |
| 40 | BENE_ESRD_IND | Defined | Defined | Defined | Validated | Yes |

## FINAL SUMMARY
CLEANED DATA VALIDATION: PASS
40-FEATURE DATASET: PASS
POINT-IN-TIME SAFETY: PASS
DATA LEAKAGE: PASS
READY FOR MODEL BENCHMARKING: YES
