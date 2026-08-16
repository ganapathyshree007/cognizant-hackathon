# Step 6: Navigation Opportunity

## 1. Purpose
The Navigation Opportunity Engine (Step 6) operates immediately downstream of the Deterministic Safety Gate. Its sole purpose is to evaluate whether a member's historical utilization pattern indicates a POTENTIAL opportunity for lower-acuity care navigation, independent of their raw risk of returning to the ED.

## 2. Difference Between Repeat ED Risk and Navigation Opportunity
- **Repeat ED Risk** (Step 4) predicts the likelihood of another ED visit within 90 days. It makes no judgment on whether that visit is avoidable.
- **Navigation Opportunity** (Step 6) interprets that risk alongside historical outpatient/inpatient patterns. A patient with high risk but also high chronic inpatient needs may not be a good candidate for diversion, whereas a patient with high risk and zero recent outpatient follow-up presents a strong opportunity for care management.

## 3. Input Features
Step 6 consumes point-in-time features derived from the historical CMS claims pipeline:
- `risk_score` (from the XGBoost model)
- `ed_visits_90d`
- `ed_visits_365d`
- `outpatient_visits_90d`
- `inpatient_visits_90d`

## 4. Scoring Methodology
The engine calculates a `navigation_opportunity_score` (0-100) deterministically:
- **Risk Base**: Up to 40 points awarded based on the raw `risk_score`.
- **ED Frequency**: Up to 30 points awarded for repeated/recent ED utilization.
- **Care Continuity**: Up to 30 points awarded if the patient lacks outpatient follow-up.
- **Acuity Context (Negative Modifier)**: Score is penalized (-20) if the patient has significant recent inpatient utilization, acknowledging legitimate clinical complexity.

## 5. Score Interpretation
- `HIGH` (70-100): Strong utilization pattern suggesting intervention is warranted.
- `MEDIUM` (40-69): Moderate indicators for potential navigation.
- `LOW` (0-39): Weak historical evidence supporting automated diversion.

## 6. Evidence Generation
The engine outputs structured JSON containing the calculated score, the categorical level, the exact numerical evidence consumed, and deterministic string `drivers` explaining the calculation (e.g., `LOW_OUTPATIENT_UTILIZATION`).

## 7. Safety Gate Dependency
Navigation Opportunity can **only** be evaluated if a valid Safety Session verifies the status is `NO_EMERGENCY_INDICATOR`. If the safety status is `POSSIBLE_EMERGENCY` or `INSUFFICIENT_INFORMATION`, the opportunity calculation is explicitly blocked.

## 8. Leakage Prevention
The endpoint consumes features strictly pre-calculated up to the index date by the Step 4 v2 feature pipeline. Future information is structurally isolated from this scoring module.

## 9. Missing-Data Behavior
If critical access features (such as PCP attribution) are missing from the raw data, the engine explicitly flags them as `DATA_UNAVAILABLE` rather than defaulting to "low engagement." 

## 10. Limitations
- The underlying ED classification relies solely on HCPCS codes.
- True clinical context (like detailed physician notes) is unavailable.
- PCP network relationships are simulated/absent.

## 11. Not an Avoidability Classifier
**The Navigation Opportunity Score is a transparent prototype decision-support score based on historical utilization evidence. It is not a clinically validated score and does not establish that an ED visit was avoidable or inappropriate.**

## 12. Versioning
Currently running `NAV_OPP_V1`.
