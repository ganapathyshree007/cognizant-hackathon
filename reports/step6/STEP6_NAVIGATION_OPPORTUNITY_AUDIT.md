# Step 6 Navigation Opportunity Audit

## 1. Executive Summary
The backend successfully isolates the deterministic Safety Gate (Step 5) and correctly leverages a strict, temporal-leakage-free Repeat ED Risk Model. However, **Step 6 (Navigation Opportunity) is completely missing.** The system incorrectly skips from `risk_band` directly to pathway generation without evaluating a distinct "Navigation Opportunity" score. A high repeat-ED risk is conflated with an opportunity for lower-acuity navigation, which is clinically flawed since some high-risk ED utilizers may require ED care. 

## 2. Existing Step 6 Architecture
There is no dedicated Step 6 layer. The `/v1/pathways` endpoint in `backend/main.py` directly consumes the `risk_band` output from the ML model and performs basic string matching on text drivers (`"No outpatient"`) to assign pathways (`PRIMARY_CARE` or `CARE_MANAGEMENT`). 

## 3. Existing Features
Historical features are rigorously calculated in `cms_pipeline.py` and `improve_data_investigation.py` (v2 enhanced features).

## 4. Feature Availability Matrix
| Feature | Exists? | Source | Exact Column | Used in Step 6? |
| :--- | :--- | :--- | :--- | :--- |
| total ED visits | YES | `cms_pipeline.py` / `improve_data_investigation.py` | `total_ed_visits` / `ed_visits_{window}d` | NO |
| ED visits in 90 days | YES | `improve_data_investigation.py` | `ed_visits_90d` | NO |
| days since previous ED visit | YES | `improve_data_investigation.py` | `days_since_previous_ed` | NO |
| outpatient visits | YES | `improve_data_investigation.py` | `outpatient_visits_90d` | NO |
| inpatient visits | YES | `improve_data_investigation.py` | `inpatient_visits_90d` | NO |
| PCP engagement / attribution | NO | N/A (Flagged missing in `missing_access_features.md`) | N/A | NO |
| unique diagnosis count | YES | `improve_data_investigation.py` | `unique_diagnosis_count_{window}d` | NO |
| chronic condition burden | YES | `improve_data_investigation.py` | `chronic_condition_burden` | NO |

## 5. Navigation Opportunity Score Audit
**Repeat ED Risk exists, but Navigation Opportunity is not separately implemented.** There is no calculation of `navigation_opportunity_score` or `navigation_opportunity_level` (LOW/MEDIUM/HIGH) based on evidence.

## 6. Repeat Risk vs Navigation Opportunity
**INCORRECT / PARTIALLY_IMPLEMENTED.** The system currently directly maps:
`HIGH repeat-ED risk + "No outpatient" driver → CARE_MANAGEMENT`
It conflates risk with opportunity, failing to recognize that appropriate high-risk repeat utilizers should not necessarily be diverted.

## 7. Safety Gate Integration
**PASS.** The recently fixed Safety Gate acts as a hard boundary. `POSSIBLE_EMERGENCY` and `INSUFFICIENT_INFORMATION` strictly block the automated pathway logic.

## 8. Leakage Audit
**PASS.** The v2 pipeline (`improve_data_investigation.py`) explicitly filters `prior = h.iloc[:pos]` strictly before the index date. Furthermore, demographic/chronic conditions use `coverage_year - 1` to ensure only the previous year's data is available. No temporal leakage was found.

## 9. Temporal Window Audit
**PASS.** Windows (30, 60, 90, 180, 365) are computed as `index_date - days`, explicitly excluding the index date itself and future dates.

## 10. Member Aggregation Audit
**PASS.** Grouped by `member_id` then `event_date`. Claim lines are successfully collapsed into single encounters per member-day.

## 11. ED Identification Dependency
**PASS.** Uses the strict, validated HCPCS definitions (`99281`-`99285`). 

## 12. PCP/Follow-up Signals
| Signal | Available | Reliable | Used | Source |
| :--- | :--- | :--- | :--- | :--- |
| Outpatient utilization | YES | YES | NO | `outpatient_visits_{window}d` |
| PCP Visits / Attribution | NO | NO | NO | Missing per `missing_access_features.md` |

## 13. Clinical Context Signals
Clinical condition signals exist (e.g., `chronic_condition_burden`, `repeated_diagnosis_count_90d`). However, they are simplistic counts rather than clinically meaningful clinical grouping (like CCSR).

## 14. Explainability Audit
**FAIL.** Does not generate an explainable structured evidence payload. Explanations are hardcoded strings (e.g., `"High risk and no recent outpatient utilization."`).

## 15. LLM/RAG Audit
**PASS.** LLM/RAG does not independently make safety or avoidability decisions. It only serves text-based drivers to the engine.

## 16. Scenario Testing
- **A & F (Utilization Profiles)**: Fails to produce distinct navigation opportunity scores based on utilization patterns, solely mapping risk bands.
- **B & C (Safety Halts)**: PASS. Safely halts upon emergency triggers or insufficient info.

## 17. Pathway Integration
**FAIL.** Pathway selection completely bypasses a Navigation Opportunity layer.

## 18. Missing Components
- Distinct `navigation_opportunity_score` calculation.
- Evaluation logic combining multi-signal evidence.
- Structured explanation payload.

## 19. Incorrect Components
- Direct mapping of `risk_band` to pathways without an opportunity filter.

## 20. Recommended Changes
1. Implement a distinct Step 6 module that consumes the V2 pipeline features.
2. Formulate rules combining ED recency, outpatient ratios, and condition patterns to calculate a `navigation_opportunity_score`.
3. Separate "Risk of Repeat ED" from "Opportunity for Intervention".

## 21. Priority Order
1. Build `navigation_opportunity` engine.
2. Update `/v1/pathways` to consume `navigation_opportunity` instead of `risk_band`.
3. Expose structured evidence payload for explainability.
