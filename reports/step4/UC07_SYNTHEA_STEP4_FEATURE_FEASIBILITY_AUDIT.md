# UC07 Step 4: Historical Repeat-ED Risk Prediction - Synthea Data Audit

> [!IMPORTANT]
> This is a read-only audit and design stage report. No models have been trained and no production artifacts have been modified.

## 1. Dataset Inventory

An audit of the physical Synthea CSV files in `step4_raw` was conducted.

| Table | Row Count | Col Count | Missingness / Notes | Date Range | Provides Historical Features? |
|---|---|---|---|---|---|
| **patients.csv** | 1,163 | 25 | Clean. `DEATHDATE` exists for deceased. | 1911-07-14 to 2021-09-24 | Yes (Demographics) |
| **encounters.csv** | 61,459 | 15 | Contains costs, reasons, classes. | 1912-09-26 to 2021-11-19 | Yes (Utilization, Index) |
| **conditions.csv** | 38,094 | 6 | Clean exact diagnosis codes. | 1919-06-06 to 2021-11-15 | Yes (Condition burden) |
| **medications.csv** | 56,430 | 13 | Dispenses, cost, reason. | 1922-05-22 to 2021-11-18 | Yes (Medication burden) |
| **observations.csv** | 531,144 | 9 | Includes vitals. 249 duplicates. | 1932-06-21 to 2021-11-19 | Yes (Prior clinical values) |
| **procedures.csv** | 83,823 | 9 | Base cost, reasons. | 1932-06-21 to 2021-11-19 | Yes (Procedure history) |
| **careplans.csv** | 3,931 | 9 | Care plan details. | 1912-09-25 to 2021-11-15 | Yes |
| **allergies.csv** | 794 | 15 | Allergy records. | 1912-10-08 to 2021-02-15 | Yes |
| **claims.csv** | 117,889 | 31 | Detailed financial records. | 1912-09-26 to 2021-11-19 | Yes (Cost) |
| **providers.csv** | 5,056 | 12 | Provider directory. | N/A | No |
| **organizations.csv**| 1,127 | 11 | Org directory. | N/A | No |

## 2. Validate Existing Approach (Friend's Numbers)

I directly queried the raw dataset to validate your friend's reported numbers:

| Metric | Friend's Report | Actual Audit | Assessment |
|---|---|---|---|
| Cleaned Encounters | 61,459 | 61,459 | **MATCH** |
| Total Patients | 1,163 | 1,163 | **MATCH** |
| Raw Emergency Encounters | 2,168 | 2,168 | **MATCH** |
| Excluded (< 90d follow up) | 41 | 41 | **MATCH** |
| Excluded (Death within 90d) | 72 | 36 | **DISCREPANCY** (Friend overcounted) |
| Final ED-Index Rows | 2,055 | 2,091 | **UPDATED** |
| Total Positives | N/A | 371 | Extracted from new target logic |
| Unique Patients in Index | N/A | 812 | Extracted from new target logic |

> [!WARNING]
> Your friend reported 72 exclusions due to death. The actual number of patients who died strictly within 90 days of an index ED visit is 36. We must use 2,091 index rows, not 2,055.

All 32 proposed features (Recency, Utilization, Cost, Demographics) can be successfully computed using `encounters.csv`, `claims.csv`, and `patients.csv`.

## 3. ED Definition

- **Synthea Representation:** `ENCOUNTERCLASS == 'emergency'`
- **Analysis:** This cleanly identifies ED visits without needing complex CPT/Revenue code parsing. 
- **Comparison to CMS:** CMS requires triangulating Revenue Codes (045x, 0981) and Claim Types (Inpatient/Outpatient). Synthea abstracts this away, meaning a Synthea model cannot natively run on raw CMS data without a harmonization layer that maps CMS logic into a unified "encounter class".

## 4. Target Definition

The target `repeat_ed_90d` must be constructed using exact timestamps to avoid same-day ambiguity. 

**Formal Rule:**
```python
repeat_ed_90d = 1 IF:
(NEXT_ED_START_TIMESTAMP > INDEX_ED_START_TIMESTAMP) 
AND 
(Days_between(INDEX_ED_START_TIMESTAMP, NEXT_ED_START_TIMESTAMP) <= 90)
ELSE 0
```
*Note: 1 same-day multiple-ED encounter was detected in the dataset. Using strict timestamp inequalities safely orders these events.*

## 5. Point-in-Time Feature Rule

To avoid target leakage, every historical feature must observe a strict temporal boundary:
`feature_event_timestamp < INDEX_ED_START_TIMESTAMP`

Current encounter codes, vitals recorded during the index ED visit, and the index cost are **STRICTLY PROHIBITED** from historical features.

## 6. Feature Feasibility Analysis

Your friend's utilization features are highly viable. However, Synthea allows us to capture *clinical* depth that CMS claims often lack. 

See the attached artifact `UC07_SYNTHEA_STEP4_FEATURE_CATALOG.csv` for the fully audited 50+ feature catalog. Highly recommended new features include:
- `hist_active_medication_count`
- `hist_condition_burden_90d`
- `hist_abnormal_observations_count`

## 7. Patient-Level Leakage Audit

- **Finding:** A single patient averages ~2.5 index rows in the dataset.
- **Risk:** If a patient's early encounters are in TRAIN and their later encounters are in TEST, the model might overfit to patient-specific identifiers or stable traits rather than generalizable risk factors.
- **Recommendation:** Splitting must be done using a **Grouped Patient Split** (ensuring all rows for Patient X go into the exact same fold/split).

## 8. Temporal Split Design

Due to the synthetic longitudinal nature of Synthea, a naive temporal split often creates disjoint demographics (e.g., older patients in train, younger in test). 

> [!IMPORTANT]  
> A standard Date-based Temporal Split is NOT recommended for this small, synthetic dataset because it will cause severe dataset shift artifacts. Instead, use a **Grouped-Patient K-Fold Cross Validation** or a **Patient-Stratified Split**.

## 9. Sample Size & Statistical Reliability

> [!CAUTION]
> Your friend's test set contained only **16 positives**. This is highly unstable.
> - A test set of 16 positives means every single correct/incorrect prediction swings Recall by **6.25%**. 
> - A model getting 8/16 vs 9/16 right looks like a massive performance leap but is statistically indistinguishable.

With only 2,091 total rows and 371 positives across the entire dataset, a single Train/Val/Test split is statistically unsafe. 
**We must use 5-Fold Grouped Cross Validation** for evaluation to ensure robust metrics. 

## 10. CMS vs Synthea Feature Difference

| Domain | CMS Candidate Model | Synthea Candidate Model |
|---|---|---|
| **Realism** | Real-world messy claims, missing data, noise | Perfectly structured, fully observed |
| **Financials** | Exact Medicare payments, DRGs, HCPCS | Simulated base costs |
| **Clinical** | Limited to diagnosis codes on claims | Deep clinical vitals, observations, continuous meds |

**Conclusion:** Synthea has powerful complementary signals (vitals, exact meds), but it is too "clean". It will likely achieve unrealistically high AUCs compared to the CMS model.

## 11. Current Context Boundary

The boundary is drawn strictly at the `START` timestamp of the index ED encounter.
- **Step 4 (Historical Risk):** Uses only data *prior* to index. 
- **Step 5 (Safety Gate / Current Context):** Will ingest the index encounter's `REASONCODE`, vitals from the ED observation, and current symptoms. Do NOT blend these.

## 12. Final Recommendations

- **A.** **Yes**, reproduce the 32-feature baseline, but fix the death exclusion logic (36 instead of 72).
- **B.** **Yes**, expand it using `conditions.csv` and `medications.csv` to capture clinical burden.
- **C.** **Yes**, treat Synthea as a separate Step-4 clinical validation model.
- **D.** **Yes**, CMS MUST remain the primary model due to its real-world claim complexity.
- **E.** **Yes**, test a Fusion model in the future to evaluate Claims + Clinical value.
- **F.** **No**, the current dataset (1,163 patients) is too small. **Action:** Generate a 100,000 patient Synthea dataset for the final pipeline.
- **G.** Features to use: Friend's 32 Utilization/Demo features + 15 Clinical features (Condition/Med counts).
- **H.** Methodology: **5-Fold Grouped Patient Cross-Validation**, abandoning the single 87-row test set approach to gain statistical stability.
