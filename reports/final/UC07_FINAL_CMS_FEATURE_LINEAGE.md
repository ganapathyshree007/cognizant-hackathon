# UC07 Final CMS Feature Lineage Audit

## OBJECTIVE
This report provides a complete, read-only feature lineage audit of the CMS/DE-SynPUF data pipelines powering the `repeat_ed_risk_model.joblib` XGBoost model. It separates feature extraction by source table, details the exact transformations, and proposes the final feature list based on the prior ablation studies.

---

## 1. BENEFICIARY FEATURE LINEAGE

**Source File:** `member_year_clean.csv` (Derived from CMS Beneficiary Summary)

| # | Final Feature | Source Column(s) | Transformation | Point-in-Time Rule | Currently Used? | Candidate for Final Model? |
|---|---|---|---|---|---|---|
| 1 | `age_at_year_end` | `age_at_year_end` | None (Cast to numeric) | Matches `index_year` | Yes | Yes |
| 2-5 | Coverage Months (4 feats) | `BENE_HI_CVRAGE_TOT_MONS`, `BENE_SMI_CVRAGE_TOT_MONS`, `BENE_HMO_CVRAGE_TOT_MONS`, `PLAN_CVRG_MOS_NUM` | Cast to numeric | Matches `index_year` | Yes | Yes |
| 6-16 | Chronic Flags (11 feats) | `SP_ALZHDMTA`, `SP_CHF`, `SP_CHRNKIDN`, `SP_CNCR`, `SP_COPD`, `SP_DEPRESSN`, `SP_DIABETES`, `SP_ISCHMCHT`, `SP_OSTEOPRS`, `SP_RA_OA`, `SP_STRKETIA` | "1" -> 1, Else -> 0 | Matches `index_year` | Yes | Yes |
| 17 | `chronic_condition_burden` | All `SP_*` columns above | Sum of active chronic flags | Matches `index_year` | Yes | Yes |
| 18 | `BENE_ESRD_IND` | `BENE_ESRD_IND` | "Y" -> 1, Else -> 0 | Matches `index_year` | No | **Yes** (Exp 02/03) |
| - | Target Filter | `death_date` | Drop row if `death_date <= index_date + 90` | Filter only | N/A | N/A |

---

## 2. INPATIENT FEATURE LINEAGE

**Source File:** `claim_events_clean.csv` (Derived from CMS Inpatient Claims)

| # | Final Feature | Source Column(s) | Transformation | Time Window | Point-in-Time Safe? | Currently Used? | Candidate? |
|---|---|---|---|---|---|---|---|
| 19-21 | `inpatient_visits_{30,90,365}d` | `encounter_type` ("INPATIENT") | Count distinct events | 30/90/365d | Yes (strictly `< index_date`) | Yes | Yes |
| 22 | `recent_inpatient_los` | `admission_date`, `discharge_date`, `encounter_type` | Max LOS where discharge < index | All history | Yes (Strict discharge check) | No | **No** (Redundant) |

---

## 3. OUTPATIENT FEATURE LINEAGE

**Source File:** `claim_events_clean.csv` (Derived from CMS Outpatient/Carrier Claims)

| # | Final Feature | Source Column(s) | Transformation | Time Window | Point-in-Time Safe? | Currently Used? | Candidate? |
|---|---|---|---|---|---|---|---|
| 23-25 | `outpatient_visits_{30,90,365}d` | `encounter_type` ("OUTPATIENT") | Count distinct events | 30/90/365d | Yes (`< index_date`) | Yes | Yes |
| 26-28 | `ed_visits_{30,90,365}d` | `ed_candidate_flag` | Sum of flags | 30/90/365d | Yes (`< index_date`) | Yes | Yes |
| 29 | `days_since_previous_ed` | `event_date`, `ed_candidate_flag` | Days since last ED event | All history | Yes | Yes | Yes |

---

## 4. CROSS-TABLE FEATURES

Features aggregating both Inpatient and Outpatient claims (`claim_events_clean.csv`).

| Feature | Source Tables | Source Columns | Calculation | Time Window | Leakage Risk | Candidate? |
|---|---|---|---|---|---|---|
| `all_visits_{30,90,365}d` | Inp + Out | `start_date` | Count all events | 30/90/365d | None | Yes |
| `total_paid_{30,90,365}d` | Inp + Out | `payment_amount` | Sum of payments | 30/90/365d | None | Yes |
| `diagnosis_coded_visits_{30,90,365}d` | Inp + Out | `diagnosis_codes` | Count if not null | 30/90/365d | None | Yes |
| `days_since_previous_event` | Inp + Out | `start_date` | Days since last claim | All history | None | Yes |
| `distinct_provider_count_365d` | Inp + Out | `provider_npi` | Count distinct | 365d | None | **Yes** (Exp 02/03) |
| `acute_cost_velocity_90d` | Inp + Out | `payment_amount` | `paid_30d / (paid_90d + 1)` | 90d | None | **Yes** (Exp 02/03) |
| `ed_to_outpatient_ratio_365d` | Outpatient | `ed_flag`, `enc_type` | `ed_365 / (out_365 + 1)` | 365d | None | **No** (Harmful) |

---

## 5. CURRENT MODEL FEATURES

Based strictly on `build_model_features.py` and `model_features.csv`, there are exactly **37** features entering the current XGBoost model:

1-3. `all_visits_30d`, `all_visits_90d`, `all_visits_365d`
4-6. `ed_visits_30d`, `ed_visits_90d`, `ed_visits_365d`
7-9. `outpatient_visits_30d`, `outpatient_visits_90d`, `outpatient_visits_365d`
10-12. `inpatient_visits_30d`, `inpatient_visits_90d`, `inpatient_visits_365d`
13-15. `total_paid_30d`, `total_paid_90d`, `total_paid_365d`
16-18. `diagnosis_coded_visits_30d`, `diagnosis_coded_visits_90d`, `diagnosis_coded_visits_365d`
19. `days_since_previous_event`
20. `days_since_previous_ed`
21. `age_at_year_end`
22. `BENE_HI_CVRAGE_TOT_MONS`
23. `BENE_SMI_CVRAGE_TOT_MONS`
24. `BENE_HMO_CVRAGE_TOT_MONS`
25. `PLAN_CVRG_MOS_NUM`
26-36. 11 `chronic_*` flags (Alzheimer's, CHF, Kidney, Cancer, COPD, Depression, Diabetes, Ischemic Heart, Osteoporosis, RA/OA, Stroke/TIA)
37. `chronic_condition_burden`

---

## 6. EXPERIMENTALLY VALIDATED FEATURES

From our prior experiments, we analyzed 5 candidates:

**Carried Forward (Final Candidates):**
1. `acute_cost_velocity_90d`: Captures recent acuity spikes. Selected because it dramatically reduced false positives and improved overall Precision and ROC-AUC.
2. `distinct_provider_count_365d`: Measures care fragmentation. Selected because it provided the single highest PR-AUC lift of any feature by filtering out false positives.
3. `BENE_ESRD_IND`: Binary End-Stage Renal Disease flag. Selected because it added high-purity separation (AUC lift) for the small cohort it affects.

**Rejected (Do Not Include):**
4. `ed_to_outpatient_ratio_365d`: Redundant arithmetic that starved XGBoost trees of depth capacity and actively reduced F1.
5. `recent_inpatient_los`: Hurt metrics across the board. Providing the raw length of stay was less valuable than simply providing the existence of the visit (`inpatient_visits_90d`), wasting tree splits.

---

## 7. FINAL PROPOSED FEATURE SET

**A. Beneficiary features**: `age_at_year_end`, 4 coverage month counts, 11 chronic flags, `chronic_condition_burden`, and the new `BENE_ESRD_IND`. (18 features)
**B. Inpatient features**: 3 `inpatient_visits` counts. (3 features)
**C. Outpatient features**: 3 `outpatient_visits` counts, 3 `ed_visits` counts, `days_since_previous_ed`. (7 features)
**D. Cross-table features**: 3 `all_visits` counts, 3 `total_paid` sums, 3 `diagnosis_coded_visits` counts, `days_since_previous_event`, plus the new `acute_cost_velocity_90d` and `distinct_provider_count_365d`. (12 features)

Total Proposed Features: **40**

---

## 8. FEATURE EXTRACTION FLOW

```
Beneficiary Summary → (Demographics, Chronic Flags, ESRD)
                                  ↓
Inpatient Claims ───┐     [Merge by member_id, index_year]
                    │             ↓
Outpatient Claims ──┴─→ claim_events_clean.csv (Aggregated by np.searchsorted strictly < index_date)
                                  ↓
                    Cross-table Feature Engineering (Counts, Sums, Ratios, Cost Velocity)
                                  ↓
                 Final Member + Index-Date Feature Table
                                  ↓
                   Target Labeling (future_ed within 90d)
                                  ↓
                 Train/Test Split (Temporal by index_year)
                                  ↓
                              XGBoost
```

---

## 9. FINAL TRAINING TABLE

**ONE ROW = one member's ED-candidate day.**
To prevent duplicate lines (e.g., multiple billing claims for the same ED visit) from inflating the dataset, `build_model_features.py` enforces one ED index per `member_id` and `event_date`.

- **Row Identifier**: `member_id`
- **Index Date**: `index_date` (normalized `start_date` of an ED event)
- **Feature Columns**: The 40 point-in-time features described above.
- **Target Column**: `repeat_ed_within_90d` (1 if a subsequent ED event occurs strictly within `(index_date, index_date + 90]`, else 0).
- **Columns Excluded Before Training**: `death_date` (used only to drop rows where the member died within the 90-day target window, preventing false negatives).

---

## 10. LEAKAGE AUDIT

The current pipeline uses a highly robust mechanism to prevent temporal leakage:
`np.searchsorted(dates, day, side="left")`

This mathematically guarantees that `feature_event_date < index_date`. The index event itself is *never* included in the historical features.
The target rule uses `side="right"`, mathematically guaranteeing that `target_event_date > index_date`.

**Special Date Handling:**
The only feature requiring special care was `recent_inpatient_los`, which required `discharge_date < index_date` to prevent the model from knowing the future discharge date of a patient admitted before the index event. Since `recent_inpatient_los` was **rejected**, the proposed final 40 features carry **zero temporal leakage risk**.

---

## 11. FINAL FEATURE COUNT

- Current number of model features: **37**
- Previously proposed additional features: **5**
- Rejected features: **2**
- Final proposed feature count: **40**

*List of all 40 final features*:
`all_visits_30d`, `all_visits_90d`, `all_visits_365d`, `ed_visits_30d`, `ed_visits_90d`, `ed_visits_365d`, `outpatient_visits_30d`, `outpatient_visits_90d`, `outpatient_visits_365d`, `inpatient_visits_30d`, `inpatient_visits_90d`, `inpatient_visits_365d`, `total_paid_30d`, `total_paid_90d`, `total_paid_365d`, `diagnosis_coded_visits_30d`, `diagnosis_coded_visits_90d`, `diagnosis_coded_visits_365d`, `days_since_previous_event`, `days_since_previous_ed`, `age_at_year_end`, `BENE_HI_CVRAGE_TOT_MONS`, `BENE_SMI_CVRAGE_TOT_MONS`, `BENE_HMO_CVRAGE_TOT_MONS`, `PLAN_CVRG_MOS_NUM`, `chronic_alzhdmta`, `chronic_chf`, `chronic_chrnkidn`, `chronic_cncr`, `chronic_copd`, `chronic_depressn`, `chronic_diabetes`, `chronic_ischmcht`, `chronic_osteoprs`, `chronic_ra_oa`, `chronic_strketia`, `chronic_condition_burden`, `BENE_ESRD_IND`, `distinct_provider_count_365d`, `acute_cost_velocity_90d`.

---

## 12. FINAL DECISION

1. **Which exact columns from Beneficiary are used?** `age_at_year_end`, coverage months (`BENE_HI_CVRAGE_TOT_MONS`, etc.), `SP_*` chronic indicators, `death_date` (for target filtering), and `BENE_ESRD_IND`.
2. **Which exact columns from Inpatient are used?** Handled via `claim_events_clean.csv`: `encounter_type` ("INPATIENT") and `start_date`.
3. **Which exact columns from Outpatient are used?** Handled via `claim_events_clean.csv`: `encounter_type` ("OUTPATIENT"), `ed_candidate_flag`, and `start_date`.
4. **Which features are derived across tables?** `all_visits`, `total_paid`, `diagnosis_coded_visits`, `days_since_previous_event`, `distinct_provider_count_365d`, `acute_cost_velocity_90d`.
5. **Which features should enter the final XGBoost model?** The 37 base features + `BENE_ESRD_IND`, `distinct_provider_count_365d`, and `acute_cost_velocity_90d`. (Total 40).
6. **Which features should be excluded?** `recent_inpatient_los` and `ed_to_outpatient_ratio_365d`.
7. **Are all final features point-in-time safe?** Yes. Handled via strictly bounded `<` array slicing.
8. **Is there any remaining leakage risk?** No. The target horizon correctly handles death dates, and the predictors strictly omit the index event.
9. **What should the final feature-building pipeline look like?** The existing `build_model_features.py` script should be modified to add the Provider counting logic, compute the ESRD flag during the Beneficiary merge, and calculate `acute_cost_velocity_90d` via simple division before saving. No structural loop changes are required.
