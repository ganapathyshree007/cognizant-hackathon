# Step 6: Implementation Report

## A. Existing Implementation Found
The previous audit confirmed that Step 6 was completely missing. The backend `/v1/pathways` endpoint was directly mapping the Step 4 Repeat ED risk band (`HIGH`) into care management pathways, conflating the risk of returning to the ED with the clinical opportunity to divert the patient to lower-acuity care.

## B. Changes Made
- Created `backend/opportunity_engine.py` to calculate a transparent, deterministic Navigation Opportunity Score.
- Updated `backend/main.py` database schema to include an `opportunity_sessions` table.
- Added a `POST /v1/navigation-opportunity` endpoint to lock in server-derived scores.
- Rerouted `POST /v1/pathways` to depend on `opportunity_session_id`, fundamentally breaking the old `risk_band -> pathway` bypass.
- Created `test_navigation_flow.py` (10 tests) and updated `test_safety_gate.py` to assert correct chaining.

## C. Features Used
- `risk_score` (Extracted from knowledge graph features)
- `ed_visits_90d`
- `ed_visits_365d`
- `outpatient_visits_90d`
- `inpatient_visits_90d`

## D. Scoring Formula
The engine scales the XGBoost risk score (up to 40 pts). It adds up to 30 pts for recent ED frequency. It adds up to 30 pts for lack of outpatient continuity. Crucially, it subtracts 20 pts if the patient has had >= 2 inpatient visits, dynamically deprioritizing patients whose complex clinical context warrants recurring high-acuity care.

## E. Score Thresholds
- **HIGH**: >= 70
- **MEDIUM**: 40 - 69
- **LOW**: < 40

## F. Evidence Generation
Outputs a structured JSON trace, recording the raw numeric inputs and generating discrete logical drivers like `REPEATED_ED_UTILIZATION` and `HIGH_INPATIENT_ACUITY_CONTEXT`.

## G. Safety Gate Integration
The `/v1/navigation-opportunity` endpoint explicitly queries the `safety_sessions` table. If the session status is anything other than `NO_EMERGENCY_INDICATOR`, it returns a 400 blocking error.

## H. Pathway Integration
`/v1/pathways` was decoupled from raw risk. It now requires an `opportunity_session_id` and filters logic based on the calculated `opportunity_level`. 

## I. Leakage Verification
All inputs are fed from the existing knowledge graph output and V2 CMS pipeline, which strictly limit features to those present structurally *before* the index encounter date.

## J. Test Results
`test_navigation_flow.py` executed and passed 10/10 scenarios, confirming boundary limits, modifier functionality, missing data handling, and client override prevention.

## K. Regression Results
`test_safety_gate.py` executed and passed 15/15 scenarios, confirming that the deterministic Safety Gate authority remains fundamentally intact and continues blocking pathway execution when an emergency or insufficient data is detected.

## L. Files Modified
- `backend/main.py`
- `test_safety_gate.py`

## M. Files Created
- `backend/opportunity_engine.py`
- `test_navigation_flow.py`
- `NAVIGATION_OPPORTUNITY.md`
- `STEP6_IMPLEMENTATION_REPORT.md`

## N. Known Limitations
PCP engagement/attribution features are currently mocked as `DATA_UNAVAILABLE` because they do not exist natively in the prototype CMS claims dataset.
