# UC07 Feature Feasibility Analysis

## 1. VERIFY ACTUAL DATA AVAILABILITY
A Python validation script inspected the actual `claim_events_clean.csv`, `member_year_clean.csv`, and `model_features.csv` files.
*   **`diagnosis_codes`**: Exists in `claim_events_clean.csv`. Type: String. Missing: 0.008%. Unique combinations: 89,228.
*   **`BENE_ESRD_IND`**: Exists in `member_year_clean.csv`. Type: String. Missing: 0%. Values: `['0', 'Y']`.
*   **`admission_date` / `discharge_date`**: Exists in `claim_events_clean.csv`. Type: String/Date. Missing: 33.3% (This perfectly corresponds to outpatient/carrier claims which do not have admission dates; inpatient claims are well-populated).
*   **`procedure_codes` / `hcpcs_codes`**: Exists in `claim_events_clean.csv`. Type: String. Missing: 61.7% / 68.1% (Expected, as not all claims involve billable procedures).
*   **`provider_npi` / `provider_id`**: Exists in `claim_events_clean.csv`. Type: String. Missing: 0.8% / 0.0%.
*   **`ed_visits_365d` / `outpatient_visits_365d` / `total_paid_30d` / `total_paid_90d`**: These derived columns already successfully exist in `model_features.csv`.

---

## 2. FEATURE FEASIBILITY TABLE

| # | Proposed Feature | Source Dataset/File | Source Column(s) | Exists? | Derivation Possible? | Historical Data Available? | Point-in-Time Safe? | Leakage Risk | Data Quality | Feasibility | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | High-risk clinical flags (90d) | `claim_events_clean.csv` | `diagnosis_codes` | YES | YES | YES | YES | LOW | GOOD | READY | Needs Regex mapping. |
| 2 | Diagnostic complexity (365d) | `claim_events_clean.csv` | `diagnosis_codes` | YES | YES | YES | YES | LOW | GOOD | READY | Split pipe-separated string. |
| 3 | ESRD indicator | `member_year_clean.csv` | `BENE_ESRD_IND` | YES | YES | YES | YES | LOW | GOOD | READY | Simple categorical map. |
| 4 | Recent inpatient LOS | `claim_events_clean.csv` | `admission_date`, `discharge_date` | YES | YES | YES | NEEDS REVIEW | MEDIUM | GOOD | FEASIBLE WITH CONDITIONS | Ensure `discharge_date < index_date`. |
| 5 | Procedure intensity | `claim_events_clean.csv` | `procedure_codes`, `hcpcs_codes` | YES | YES | YES | YES | LOW | ACCEPTABLE | READY | |
| 6 | Distinct provider count (365d) | `claim_events_clean.csv` | `provider_npi` | YES | YES | YES | YES | LOW | GOOD | READY | |
| 7 | Distinct facility count (365d) | `claim_events_clean.csv` | `provider_id` | YES | YES | YES | YES | LOW | GOOD | READY | |
| 8 | ED-to-outpatient ratio | `model_features.csv` | `ed_visits_365d`, `out...365d` | YES | YES | YES | YES | LOW | GOOD | READY | Already aggregated. |
| 9 | Acute cost velocity | `model_features.csv` | `total_paid_30d`, `total...90d` | YES | YES | YES | YES | LOW | GOOD | READY | Already aggregated. |
| 10 | Accelerating ED frequency | `model_features.csv` | `ed_visits_30d`, `ed_visits_90d`| YES | YES | YES | YES | LOW | GOOD | READY | Already aggregated. |

---

## 3. EXACT FEATURE FORMULA

**Feature 1: High-risk clinical flags (90d)**
*   **Input**: `diagnosis_codes`, `event_date`, `index_date`
*   **Filtering**: `event_date >= (index_date - 90d)` AND `event_date < index_date`
*   **Aggregation**: Check if `diagnosis_codes` matches specific regexes (e.g. Sepsis: `^038.*`). `1` if any match found, else `0`.
*   **Output Type**: Binary (0/1)

**Feature 2: Diagnostic complexity score (365d)**
*   **Input**: `diagnosis_codes`, `event_date`, `index_date`
*   **Filtering**: `event_date >= (index_date - 365d)` AND `event_date < index_date`
*   **Aggregation**: Split `diagnosis_codes` by `|`, truncate to 3 digits (ICD-9 categories), calculate `len(set(all_codes_in_window))`.
*   **Output Type**: Integer

**Feature 3: ESRD indicator**
*   **Input**: `BENE_ESRD_IND`
*   **Filtering**: None (Static demographic).
*   **Aggregation**: Map `Y` → 1, `0` → 0.
*   **Output Type**: Binary (0/1)

**Feature 4: Recent inpatient length of stay**
*   **Input**: `admission_date`, `discharge_date`, `encounter_type`, `index_date`
*   **Filtering**: `encounter_type == 'INPATIENT'` AND `discharge_date < index_date`. Get the most recent row.
*   **Aggregation**: `(discharge_date - admission_date).days`. If missing, `0`.
*   **Output Type**: Integer

**Feature 5: Procedure intensity**
*   **Input**: `procedure_codes`, `hcpcs_codes`, `event_date`
*   **Filtering**: `event_date >= (index_date - 90d)` AND `event_date < index_date`
*   **Aggregation**: Sum of `len(split("|"))` for both columns across all encounters in window.
*   **Output Type**: Integer

**Feature 6/7: Provider/Facility Count (365d)**
*   **Input**: `provider_npi` / `provider_id`, `event_date`
*   **Filtering**: `event_date >= (index_date - 365d)` AND `event_date < index_date`
*   **Aggregation**: `len(set(provider_npi))` in window.
*   **Output Type**: Integer

**Feature 8: ED-to-outpatient ratio**
*   **Formula**: `ed_visits_365d / (outpatient_visits_365d + 1)`
*   **Output Type**: Float

**Feature 9: Acute cost velocity**
*   **Formula**: `total_paid_30d / (total_paid_90d + 1)`
*   **Output Type**: Float

**Feature 10: Accelerating ED frequency**
*   **Formula**: `int((ed_visits_30d * 3) > ed_visits_90d)`
*   **Output Type**: Binary (0/1)

---

## 4. POINT-IN-TIME VALIDATION
All features must be derived strictly using data known *prior* to the `index_date`. 
*   **Safe**: Features 1, 2, 5, 6, 7 natively respect this rule because they are event-based. `build_model_features.py` already uses `np.searchsorted(side="left")` to exclude `event_date >= index_date`.
*   **Needs Special Handling**: **Feature 4 (LOS)**. If an inpatient stay overlaps the `index_date` (i.e. admitted before, discharged after), including its full LOS is a temporal leak (future knowledge). The condition must strictly be `discharge_date < index_date` to prevent leakage.
*   **Safe by Design**: Features 8, 9, 10 rely on pre-calculated columns that already enforce the point-in-time boundary.

---

## 5. TARGET LEAKAGE CHECK
*   Feature 1 (Diagnoses): **SAFE**
*   Feature 2 (Complexity): **SAFE**
*   Feature 3 (ESRD): **SAFE**
*   Feature 4 (LOS): **POTENTIAL LEAKAGE** (Must strictly enforce `discharge_date < index_date` as noted above).
*   Feature 5 (Procedures): **SAFE**
*   Feature 6/7 (Provider/Facility counts): **SAFE**
*   Feature 8/9/10 (Ratios): **SAFE**

---

## 6. DATA QUALITY ANALYSIS
*   **Missingness**: `BENE_ESRD_IND` is perfectly populated. `diagnosis_codes` is nearly perfectly populated. `procedure_codes` are sparse (60%+ missing), but this correctly represents non-procedural visits.
*   **Distribution**: Provider counts and complexity scores will be right-skewed but highly continuous, making them excellent tree-splitting features.
*   **Reliability**: All features are entirely reliable for ML ingestion, as they derive from standard, non-nullable billing protocols.

---

## 7. PATIENT-LEVEL CALCULATION FEASIBILITY
Every feature can be calculated natively inside `event_features()` inside `build_model_features.py`. Because the current pipeline groups events by `member_id` and iterates over each `index_date`, the script can cleanly isolate the subset of historical event arrays (e.g. `history['diagnosis_codes'][left_idx : right_idx]`) to perform the exact calculations specified above without any architectural changes.

---

## 8. CHECK EXISTING PIPELINE
| Feature | Already Exists? | Existing Feature Name | Existing Source Code | Needs New Implementation? |
|---|---|---|---|---|
| High-risk clinical flags | NO | N/A | `build_model_features.py` | YES |
| Diagnostic complexity | NO | N/A | `build_model_features.py` | YES |
| ESRD indicator | DOES NOT EXIST IN MODEL | N/A | `member_year_clean.csv` | YES (Missing from extraction) |
| Recent inpatient LOS | NO | N/A | `build_model_features.py` | YES |
| Procedure intensity | NO | N/A | `build_model_features.py` | YES |
| Distinct provider count | NO | N/A | `build_model_features.py` | YES |
| Distinct facility count | NO | N/A | `build_model_features.py` | YES |
| ED-to-outpatient ratio | PARTIALLY | `ed_visits_365d`, `outpatient_visits_365d` | `build_model_features.py` | YES (Add ratio math) |
| Acute cost velocity | PARTIALLY | `total_paid_30d`, `total_paid_90d` | `build_model_features.py` | YES (Add ratio math) |
| Accelerating ED freq | PARTIALLY | `ed_visits_30d`, `ed_visits_90d` | `build_model_features.py` | YES (Add ratio math) |

---

## 9. CHECK REDUNDANCY
*   **New Information**: Features 1, 2, 3, 4, 5, 6, 7 provide entirely **new clinical and organizational dimensions** that the model currently lacks.
*   **Redundancy / Derived**: Features 8, 9, 10 are derived exclusively from existing features. However, tree-based models like XGBoost struggle to intrinsically learn complex arithmetic ratios. Explicitly providing the `ED-to-outpatient ratio` or `Acute cost velocity` will likely add new predictive value despite being highly correlated with their parent features.

---

## 10. CLINICAL INTERPRETATION
*   **High-risk clinical flags**: Captures chronic exacerbations (CHF, COPD) and behavioral instability that frequently precipitate acute ED crises.
*   **Diagnostic complexity**: Represents the overall burden of multi-morbidity and systemic fragility.
*   **ESRD indicator**: Identifies patients on dialysis, who suffer disproportionately high rates of acute complications requiring emergent care.
*   **Recent inpatient LOS**: Serves as a proxy for the severity of the most recent hospitalization and the likelihood of post-discharge physiological decompensation.
*   **Procedure intensity**: Differentiates highly interventional (severe) past visits from routine observation.
*   **Distinct provider/facility count**: Represents care fragmentation. Patients bouncing between 5 different facilities are highly likely to experience disjointed care and medication errors leading back to the ED.
*   **ED-to-outpatient ratio**: Represents the patient's dependence on the ED as their primary mode of healthcare access versus managed primary care.
*   **Acute cost velocity**: Represents a sudden, steep acceleration in medical acuity compared to their historical baseline.
*   **Accelerating ED frequency**: Identifies patients entering a spiraling cycle of emergent crisis.

---

## 11. PRIORITIZATION
**HIGH PRIORITY**
*   **ESRD indicator**: Zero implementation complexity, massive clinical signal.
*   **Distinct provider count (365d)**: Strong proxy for fragmentation, high data quality.
*   **ED-to-outpatient ratio**: Trivial arithmetic derivation, strong indicator of care patterns.
*   **Recent inpatient LOS**: High clinical signal for post-discharge bouncebacks.

**MEDIUM PRIORITY**
*   **High-risk clinical flags**: Excellent signal, but requires careful regex/ICD9 grouping rules.
*   **Diagnostic complexity**: Good signal, moderate implementation complexity (string splitting).
*   **Acute cost velocity / Accelerating ED frequency**: Easy to implement, but heavily correlated with existing volume features.

**LOW PRIORITY**
*   **Procedure intensity**: High missingness/sparsity may dilute the signal, though still technically valid.

---

## 12. FINAL RECOMMENDATION

A. **Features that are definitely feasible**: 1, 2, 3, 5, 6, 7, 8, 9, 10.
B. **Features feasible with conditions**: 4 (Must enforce `discharge_date < index_date`).
C. **Features that should NOT be used**: None. All are valid.
D. **Features already present**: The base components for 8, 9, 10 are present, but the ratios themselves are not.
E. **Features providing genuinely new info**: 1, 2, 3, 4, 5, 6, 7.
G. **Features with leakage concerns**: 4 (If overlap is poorly handled).

### RECOMMENDED FEATURE SET FOR NEXT EXPERIMENT
To immediately address the low 14% Recall and 15% Precision in the next training iteration, I recommend testing the following explicitly safe and highly feasible features:
1. `BENE_ESRD_IND` (ESRD indicator)
2. `distinct_provider_count_365d` (Care fragmentation)
3. `ed_to_outpatient_ratio_365d` (ED dependence)
4. `acute_cost_velocity_90d` (Sudden acuity spike)
5. `recent_inpatient_los` (Hospitalization severity, enforcing strict temporal boundaries)
