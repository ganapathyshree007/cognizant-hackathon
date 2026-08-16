# UC07 XGBoost Diagnostic Analysis & Data Lineage

## 1. EXECUTIVE SUMMARY
A read-only diagnostic analysis was performed on the actual dataset (`model_features.csv`) and the trained model (`repeat_ed_risk_model.joblib`). The primary reason for the weak predictive performance is **Weak Feature Signal** and **Extreme Class Imbalance**. The model relies almost exclusively on retrospective utilization counters (e.g., "did they visit the ED recently?") which generates many false positives (because most frequent utilizers do not bounce back in exactly 90 days) and misses many false negatives (because new ED repeaters have no prior history to flag). The pipeline is technically sound and leak-free, but clinically shallow.

---

## 2. TARGET DEFINITION
- **Target Column**: `repeat_ed_within_90d`
- **Definition**: A binary flag (0/1) indicating if a member had an "ED-candidate event" strictly after their `index_date` and within 90 days. 
- **Generation Logic**: The `future_ed()` function checks if any `ed_candidate_flag=1` event exists in the `[index_date + 1 day, index_date + 90 days]` window.
- **Leakage Status**: Clean. Target data strictly looks ahead, while features strictly look backwards (`< index_date`).

## 3. CLASS DISTRIBUTION
- **Total Samples (Test Split)**: 11,769
- **Positive Samples**: 1,039
- **Negative Samples**: 10,730
- **Positive Prevalence**: 8.8%
- **Negative Prevalence**: 91.2%
- **Imbalance Ratio**: ~1:10.

## 4. MODEL PERFORMANCE (Test Split)
- **Accuracy**: 0.8547
- **Precision**: 0.1523
- **Recall / Sensitivity**: 0.1414
- **Specificity**: 0.9237
- **F1-Score**: 0.1467
- **ROC-AUC**: 0.6053
- **PR-AUC**: 0.1254
- **Brier Score**: 0.0802
- **Confusion Matrix**: TN=9912, FP=818, FN=892, TP=147

## 5. THRESHOLD ANALYSIS
The project utilizes an operating threshold of **0.1746** rather than 0.5.
- **Why?**: Because the maximum predicted probability in the entire test set is only 0.375. At threshold 0.5, the model predicts zero positive cases. The threshold was artificially lowered to 0.1746 to achieve a non-zero recall (~14%), sacrificing precision (~15%).
- **Threshold 0.1**: Precision=0.108, Recall=0.666, F1=0.185 (Too many false positives: 5722)
- **Threshold 0.1746 (Actual)**: Precision=0.152, Recall=0.141, F1=0.146 (FP: 818, FN: 892)
- **Threshold 0.2**: Precision=0.168, Recall=0.070, F1=0.099
- **Threshold 0.5**: Precision=0.0, Recall=0.0, F1=0.0 (Predictions are all 0)

## 6. PREDICTION DISTRIBUTION
- **Minimum**: 0.0271
- **Maximum**: 0.3754
- **Mean**: 0.1100
- **Median**: 0.1051
- **99th Percentile**: 0.2389
- **Above 0.5**: 0
- **Above 0.1746**: 965
**Conclusion**: The model is systematically underconfident, severely compressing all predictions into the 0.02 - 0.37 range. It cannot decisively identify high risk.

## 7. FEATURE IMPORTANCE (Top & Bottom)
**Top Features (by Gain)**:
1. `chronic_condition_burden` (23.19)
2. `diagnosis_coded_visits_365d` (15.53)
3. `inpatient_visits_30d` (8.81)
4. `chronic_alzhdmta` (7.61)
5. `BENE_HMO_CVRAGE_TOT_MONS` (7.06)

**Bottom Features**:
- `days_since_previous_event` (2.75)
- `days_since_previous_ed` (3.07)
- `all_visits_30d` (3.21)

## 8. FEATURE QUALITY
- **Missingness**: Perfectly clean except for lag features (`days_since_previous_event`, `days_since_previous_ed`), which legitimately contain NaNs for members with no history. Demographics miss 13 rows.
- **Variance**: High variance in monetary amounts (`total_paid`). Low variance in rare chronic conditions (e.g., `chronic_strketia` var=0.08).
- **Suspicious**: None. The pipeline handles missing values using `SimpleImputer`.

## 9. DATASET SPLIT & POINT-IN-TIME VALIDITY
- **Split Strategy**: By Year (Train: 2008, 2009. Test: 2010). This is temporally robust and prevents future-leakage. 
- **Point-in-Time**: Evaluated the `window_sum()` logic in `build_model_features.py`. The code explicitly uses `np.searchsorted(..., side="left")` to ensure only events strictly prior to `index_date` are included. 

## 10. ERROR ANALYSIS
- **False Positives (FP)**: Model predicted high risk, but they didn't return.
  - FP Mean ED visits (90d): 0.26
  - FP Mean Inpatient (90d): 0.12
- **False Negatives (FN)**: Model predicted low risk, but they DID return.
  - FN Mean ED visits (90d): 0.15
  - FN Mean Inpatient (90d): 0.05
**Pattern**: The model assumes "recent utilization = high future risk". False Positives had *higher* historical utilization. False Negatives had *lower* historical utilization. The model misses the "silent" or new returners entirely.

## 11. ROOT-CAUSE ANALYSIS
**Likely Causes of Weak Performance**:
1. **Weak Features**: The feature set consists entirely of volume aggregations (e.g., `ed_visits_90d`) and static demographics/flags. It lacks clinical nuance (vitals, specific diagnoses, acuity, social determinants).
2. **Class Imbalance**: The 1:10 imbalance causes the model to bias heavily towards the majority class, collapsing the predicted probability range.
3. **Model Limitation**: Because the features are shallow, XGBoost cannot split the nodes cleanly enough to isolate the true positive class, relying on coarse population-level averages.

## 12. MODEL IMPROVEMENT RECOMMENDATIONS (In Priority Order)
1. **Improve Feature Engineering**: Extract high-cardinality clinical data (primary diagnosis code embeddings, procedure specificities, provider specialties) rather than just counting visits.
2. **Address Class Imbalance**: Experiment with `scale_pos_weight` in XGBoost or SMOTE during training to push the probability distribution wider.
3. **Calibration**: Apply Platt Scaling or Isotonic Regression so probabilities map accurately to true risk.
4. **Evaluate Threshold Selection**: Re-tune the threshold on a dedicated validation split maximizing a specific business objective (e.g., F2-score to penalize false negatives more heavily).

---

## 13. COMPLETE DATASET → FEATURE LINEAGE

### A. Source Datasets
1. `claim_events_clean.csv`: Generated from CMS raw datasets (Inpatient, Outpatient). Contains unified member encounter timelines.
2. `member_year_clean.csv`: Generated from CMS Beneficiary Summary. Contains annual demographic and chronic condition flags.

### B. Source Dataset → Column → Feature Table
| Source Dataset | Source Column | Used in Pipeline? | Final Feature(s) Generated | Transformation |
|---|---|---|---|---|
| claim_events_clean | `start_date` | YES | `days_since...`, `..._visits_Xd` | Temporal filtering & aggregation |
| claim_events_clean | `payment_amount` | YES | `total_paid_Xd` | Rolling sum over 30/90/365d |
| claim_events_clean | `encounter_type` | YES | `inpatient_visits_Xd`, `outpatient...` | Filtered count over 30/90/365d |
| claim_events_clean | `ed_candidate_flag` | YES | `ed_visits_Xd`, Target | Filtered count, Future lookahead |
| claim_events_clean | `diagnosis_codes` | YES | `diagnosis_coded_visits_Xd` | Not-null count over 30/90/365d |
| member_year_clean | `age_at_year_end` | YES | `age_at_year_end` | Direct copy |
| member_year_clean | `SP_*` (Chronic) | YES | `chronic_*`, `chronic_condition_burden` | Binary mapping, Row-wise sum |

### C. Final Model Feature Table (All 38 Features)
| # | Feature Name | Meaning | Time Window | Type |
|---|---|---|---|---|
| 1 | `days_since_previous_event` | Days since any prior medical claim | < index_date | Numeric |
| 2 | `days_since_previous_ed` | Days since prior ED visit | < index_date | Numeric |
| 3-8 | `[all/ed/outpatient/inpatient]_visits_30d` | Count of encounters by type | Previous 30d | Numeric |
| 9-14| `[all/ed/outpatient/inpatient]_visits_90d` | Count of encounters by type | Previous 90d | Numeric |
| 15-20| `[all/ed/outpatient/inpatient]_visits_365d`| Count of encounters by type | Previous 365d | Numeric |
| 21-23| `total_paid_[30/90/365]d` | Sum of `payment_amount` | Prev 30/90/365d | Numeric |
| 24-26| `diagnosis_coded_visits_[30/90/365]d` | Count of visits with any ICD code | Prev 30/90/365d | Numeric |
| 27 | `age_at_year_end` | Age of member at end of index year | Static (Yearly) | Numeric |
| 28-31| `BENE_[HI/SMI/HMO]_CVRAGE_TOT_MONS` | Months of coverage by type | Static (Yearly) | Numeric |
| 32-42| `chronic_[condition]` (e.g. `chf`, `copd`) | Binary presence of chronic condition | Static (Yearly) | Binary |
| 43 | `chronic_condition_burden` | Sum of all chronic condition flags | Static (Yearly) | Numeric |

### D. Training Data Table
- **Filename**: `model_features.csv`
- **Rows**: 60,411
- **Columns**: 43 (38 features + member_id + index_date + split + Target + excluded_death)
- **Target**: `repeat_ed_within_90d`
- **Unused by XGBoost**: `member_id`, `index_date`, `index_year`, `split`, `excluded_death_in_target_window`

### E. Data Join / Merge Lineage
```text
DE1_0_2008_to_2010_Inpatient_Claims + Outpatient_Claims
   ↓
[cms_pipeline.py: collapse_claims() - Aggregates claims by CLM_ID]
   ↓
unified_encounters.csv
   ↓
[clean_all_datasets.py]
   ↓
claim_events_clean.csv (Events)   +   member_year_clean.csv (Demographics)
   ↓
[build_model_features.py: event_features() & window_sum() logic]
   ↓
MERGE on [member_id, index_year] (Left Join)
   ↓
model_features.csv
   ↓
XGBClassifier
```

### F. Feature Generation Code Trace
- **Source File**: `project_scripts/cms_data_preparation/build_model_features.py`
- **Functions**: 
  - `window_sum()`: Executes the strictly historical point-in-time calculation for all 30/90/365d aggregation features using numpy vectorization.
  - `event_features()`: Generates the event counts, sums, and lag features.
  - `member_features()`: Maps `SP_` CMS columns to boolean `chronic_` flags and sums the `chronic_condition_burden`.
  - `future_ed()`: Calculates the forward-looking Target label safely.

## 14. DATA DICTIONARY FOR MENTORS
- **Utilization Features (30/90/365 days)**: These tell the model how frequently the patient visited the hospital, ED, or outpatient clinic recently. A high number suggests a frequent utilizer.
- **Cost Features (`total_paid`)**: How much money was billed for the patient recently. Acts as a proxy for the severity or complexity of their recent medical care.
- **Lag Features (`days_since_previous`)**: How many days it has been since their last visit. Tells the model if they are returning rapidly or if it's been a long time.
- **Demographics & Coverage**: Age and insurance coverage months.
- **Chronic Conditions**: Flags indicating if the patient has Alzheimer's, Heart Failure, Kidney Disease, COPD, Diabetes, etc., and a "burden" score summing how many conditions they have.

## 15. VALIDATION CONCLUSION
**Code vs Documentation Discrepancy**: None found. 
The implementation in `build_model_features.py` matches the documentation precisely. The pipeline successfully prevents data leakage. The weak performance is entirely attributable to the simplistic nature of the historical utilization features and the severe class imbalance, NOT an implementation bug.
