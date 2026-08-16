# Data Pipeline Audit

## 1. CMS Raw Data to Claim Collapsing
**Process:** The pipeline ingests `DE1_0_2008_to_2010_Inpatient_Claims_Sample_1.csv` and Outpatient equivalents. 
**Verification:**
*   **Claim aggregation (CLM_ID):** Rows are grouped by `DESYNPUF_ID` and `CLM_ID` via `raw.groupby(keys)`. This successfully collapses line-item segments into unified encounters.
*   **Diagnosis, Procedure, HCPCS aggregation:** Codes are extracted, melted, and aggregated into a delimited string (e.g., `|`-separated list). Handled cleanly using the `codes_join` helper function.
*   **Dates:** `CLM_FROM_DT` and others are correctly converted to datetime format and boundaries (`start_date`, `end_date`) are aggregated using `min` and `max`.

## 2. ED Identification
**Process:** The system identifies Emergency Department visits deterministically using a HCPCS code inclusion list (99281–99285).
**Verification:**
*   **Classification:** It identifies `CONFIRMED_ED` via HCPCS intersection. If HCPCS is entirely empty, it sets it to `UNKNOWN`. Otherwise, it marks `NON_ED`.
*   **Missing Features:** Revenue codes and POS (Place of Service) codes are noted as missing in the raw data, which is explicitly recognized in `missing_data_report.md`. The logic accurately works with what it has.
*   **Duplicate Handling:** The system explicitly collapses same-day ED visits down to a single member-day to avoid duplicate tracking and target inflation (line 55 in `improve_data_investigation.py`).

## 3. Point-in-Time Feature Engineering
**Process:** Generation of historical features (e.g., `ed_visits_90d`, `chronic_condition_burden`).
**Verification:**
*   **Historical Windows:** The code iterates through member histories and explicitly filters `dates < d` (where `d` is the index date). 
*   **Beneficiary Linkage:** Beneficiary summary data (for chronic conditions and demographics) is strictly linked to the *prior* calendar year to prevent future information leakage (`coverage_year = y`, `available_year = index_year - 1`). 
*   **Future Information Leakage:** Features are engineered correctly without leakage. The metadata and target columns are stripped from the `model_ready_v2.csv` dataset, confirming separation.

## Conclusion
Every feature used at prediction time in the `model_ready_v2.csv` dataset existed BEFORE the prediction/index date. The claim collapsing, ED identification, and point-in-time rules are robust and prevent data leakage.
