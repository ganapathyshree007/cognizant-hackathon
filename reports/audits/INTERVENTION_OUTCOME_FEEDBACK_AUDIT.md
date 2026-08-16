# Intervention, Outcome, and Patient History Feedback Audit

## 1. Existing intervention implementation
Intervention creation is strictly locked down and explicitly requires a valid `review_id` referencing a Human Care Manager's decision (`APPROVE` or `MODIFY`). The intervention table captures relevant pathways, reviewers, and links directly back to the human decision.

## 2. Existing outcome implementation
The `POST /v1/interventions/{intervention_id}/outcomes` endpoint computes observational outcomes. It reads from the underlying `claim_events_clean.csv` to detect repeat ED visits, outpatient follow-ups, and inpatient events. The outcome records are saved in the `outcomes` table.

## 3. Existing patient-history implementation
**Missing**. The outcome is calculated and stored in the SQLite `outcomes` table, but there is no implemented mechanism to feed this information back into the member's historical record (e.g., `evidence_graph.sqlite`) or trigger new feature generation. Feedback persistence exists, but ML feature feedback integration is not implemented.

## 4. Intervention authorization
Interventions are correctly authorized. They strictly require a valid `review_id` mapped to an `APPROVE` or `MODIFY` decision. Client overrides are blocked.

## 5. Human decision linkage
Interventions are perfectly linked to the human decision via the `review_id` foreign key.

## 6. Safety Gate linkage
The Safety Gate is natively enforced through the `provider_session_id` session chain verification during the Care Manager review phase, which gates the intervention.

## 7. Provider linkage
The intervention links to the `care_manager_reviews` table, which perfectly anchors to the `provider_session_id`.

## 8. Outcome linkage
Outcomes are explicitly linked to `intervention_id`, which subsequently traces back to the case and member.

## 9. Observation window
The system supports a configurable observation window (default `window_days: int = 90`). It calculates outcomes both relative to the `index_date` and the `intervention_date` (`POST_INTERVENTION`).

## 10. Feedback-loop behavior
**Missing**. While the outcomes are stored in a database, there is no pipeline implemented to update historical data or integrate new claims back into the feature generation system.

## 11. Temporal leakage controls
Because the feedback loop is unimplemented, temporal leakage into historical ML features is structurally impossible at this time. The outcome calculation itself correctly limits its window to `start_date > anchor_date`.

## 12. Model retraining behavior
**Not implemented**. The XGBoost model operates as a static point-in-time scoring engine. No retraining pipeline exists for the prototype, which is acceptable for its current scope but noted as a limitation.

## 13. Duplicate handling
**Incorrect / Unhandled**. The `POST /v1/interventions` and `POST /v1/interventions/{intervention_id}/outcomes` endpoints do not check for existing records. Submitting the same request multiple times generates duplicate `intervention_id` and `outcome_id` UUIDs in the database.

## 14. Failure handling
Failure handling is robust. If a review, provider session, or intervention does not exist, explicit HTTP 404 exceptions are raised rather than causing silent corruption.

## 15. Causal interpretation limitations
The outcome endpoint correctly qualifies its observations: `"notice": "Index outcomes measure subsequent utilization; post-intervention outcomes measure follow-up after the recorded intervention. Claims absence is not proof of success."` It successfully avoids claiming causality.

## 16. Missing functionality
- ML feature feedback integration (patient history updates).
- Automatic model retraining (documented prototype limitation).

## 17. Incorrect functionality
- Lack of idempotency / duplicate protection for Interventions and Outcomes.

## 18. Recommended next steps
1. Implement duplicate protection (idempotency constraints) for both the `interventions` and `outcomes` tables.
2. Build a feedback pipeline to append new claims/outcomes to the historical `evidence_graph.sqlite` so future predictions utilize updated clinical history.
