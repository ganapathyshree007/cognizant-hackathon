# UC07 End-to-End Traceability Audit

This document provides a complete trace of one member journey through the verified Avoidable Emergency Department Utilization Navigator (UC07).

## 1. CMS Data Pipeline & Feature Engineering
- **Model/Method**: Reads claims data, generates point-in-time features, constructs `evidence_graph.sqlite`.
- **API Function**: Represented internally by `kg_case(case_id)` in `backend/main.py`.
- **Input**: Raw CMS claims (synthetically generated).
- **Output**: Point-in-time risk features (e.g., `ed_visits_90d`, `outpatient_visits_90d`) and extracted text `drivers`.
- **Status**: Implemented and verified by the data pipeline scripts.

## 2. XGBoost Repeat ED Risk Model
- **Model/Method**: `joblib.load('repeat_ed_risk_model.joblib')` - XGBClassifier.
- **API Function**: `POST /v1/score`
- **Input**: Point-in-time `features` JSON.
- **Output**: `risk_score` (probability) and `risk_band` (`HIGH` or `LOW`).
- **Test Evidence**: Passes all integration tests; explicitly verified to execute offline prediction.

## 3. Safety Gate
- **Model/Method**: Deterministic rule-based evaluation `evaluate_safety(context, attempt_count)`.
- **API Function**: `POST /v1/safety/assess`
- **Database Table**: `safety_sessions`
- **Input**: Case/patient context (`case_id`, `patient_id`, `new_context`).
- **Output**: `safety_status` (e.g., `NO_EMERGENCY_INDICATOR`, `POSSIBLE_EMERGENCY`), `session_id`.
- **Security Check**: This `session_id` acts as the root of the entire trust chain.

## 4. Navigation Opportunity
- **Model/Method**: Threshold mapping engine (`calculate_opportunity(risk)`).
- **API Function**: `POST /v1/navigation-opportunity`
- **Database Table**: `opportunity_sessions`
- **Input**: `case_id`, `safety_session_id`.
- **Security Check**: The backend queries `safety_sessions` using the provided `safety_session_id`. If the status is not `NO_EMERGENCY_INDICATOR`, it strictly blocks the evaluation.
- **Output**: `opportunity_level` (e.g., `HIGH`), `opportunity_id`.

## 5. Driver Analysis
- **Model/Method**: Deterministic matching mapping clinical/social drivers (`generate_drivers(risk, opportunity_level)`).
- **API Function**: `POST /v1/navigation-drivers`
- **Database Table**: `driver_sessions`
- **Input**: `opportunity_session_id`, `case_id`.
- **Security Check**: The backend verifies `opportunity_session_id` → `safety_session_id` to ensure no emergency flag was raised before producing drivers.
- **Output**: `drivers` list, `driver_session_id`.

## 6. Pathway Recommendation
- **Model/Method**: Logic mapping drivers to intervention pathways (`recommend_pathways(...)`).
- **API Function**: `POST /v1/pathways`
- **Database Table**: `pathway_sessions`
- **Input**: `driver_session_id`, `case_id`.
- **Security Check**: Re-verifies the full chain back to `safety_sessions`. If `reviewer_cleared` is false or the safety gate triggered, it blocks the recommendation.
- **Output**: `recommended_pathway` (e.g., `PRIMARY_CARE`), `pathway_session_id`.

## 7. Provider Recommendation
- **Model/Method**: SQLite SQL lookup filtering on NPI, specialty, state, and telehealth availability.
- **API Function**: `POST /v1/providers/recommend`
- **Database Table**: `provider_sessions`
- **Input**: `pathway_session_id`, `state`, `require_telehealth`.
- **Security Check**: Server explicitly queries `pathway_sessions` → `driver_sessions` → `opportunity_sessions` → `safety_sessions`. It refuses to execute the DB query if `safety_status` is emergency-related.
- **Output**: `provider_results` list, `provider_session_id`.

## 8. Care Manager Review
- **Model/Method**: Human-in-the-loop decision capture.
- **API Function**: `POST /v1/care-manager/review`
- **Database Table**: `care_manager_reviews`
- **Input**: `provider_session_id`, `reviewer_id`, `decision` (APPROVE/MODIFY/REJECT/ESCALATE).
- **Security Check**: Performs a full chain verification. Validates that the original pathway matches the AI recommendation. Does NOT allow the client to alter the original recommendation history.
- **Output**: `review_id`, `status`.

## 9. Intervention Execution
- **Model/Method**: Idempotent persistence of operational intervention event.
- **API Function**: `POST /v1/interventions`
- **Database Table**: `interventions`
- **Input**: `review_id`.
- **Security Check**: Intervention is completely blocked unless the `care_manager_reviews` table contains an `APPROVE` or `MODIFY` decision for the exact `review_id`.
- **Output**: `intervention_id`.

## 10. Observation Outcome
- **Model/Method**: Observational calculation over `claim_events_clean.csv` (`outcome_for_anchor`).
- **API Function**: `POST /v1/interventions/{intervention_id}/outcomes`
- **Database Table**: `outcomes`
- **Input**: `intervention_id`, `window_days`.
- **Output**: Repeat ED boolean, outpatient follow-up boolean, `outcome_id`.

## 11. Patient History Feedback
- **Model/Method**: Direct append-only logging of operational history to `member_history`.
- **API Integration**: Triggered automatically by successful `POST /v1/interventions` and `POST /v1/interventions/outcomes`.
- **Database Table**: `member_history`
- **Output**: Point-in-time `INTERVENTION` and `OUTCOME` records tied to `member_id` and `event_date`.

## Future Scoring Integration (Documented, Not Executed)
The future scoring loop is completely decoupled from the current pipeline. For future predictions, the feature pipeline is designated to query `member_history` where `event_date <= prediction_date` and pass the new features to the existing XGBoost model. *This pipeline step relies on scheduled batch processes outside the scope of the real-time API.*

## Audit Conclusion
**COMPLETE AND VERIFIED.** 
- **No Bypasses**: The API relies on internal database foreign keys traversing backward `intervention -> review -> provider -> pathway -> driver -> opportunity -> safety`. Clients only possess the leaf ID of their current step and cannot fabricate earlier contexts.
- **No Emergency Redirection**: At every critical junction (`pathway`, `provider`, `review`), the code explicitly re-queries the root `safety_status` and blocks lower-acuity workflows if an emergency flag is present.
- **No Temporal Leakage**: Because operational history (`member_history`) is fully distinct from raw claims, and outcome calculations rely strictly on `start_date > anchor_date`, backward leakage of future information is structurally prohibited.
- **Idempotency**: All leaf actions (Intervention/Outcome generation) are idempotent, preventing data duplication.
