# UC07 FINAL ARCHITECTURE

## 1. Problem Statement
"Some ER visits could have been a cheaper same-day clinic or telehealth call instead. Build a system that spots patterns of potentially avoidable ED use and recommends a lower-acuity next step — primary care, urgent care, telehealth, or a care-management follow-up — without ever implying a true emergency should be blocked."

## 2. Our Understanding
The system is a payer-side / care-management navigation and decision-support prototype. It is NOT an emergency department gatekeeper, hospital admission system, diagnosis system, autonomous clinical triage, or an automatic patient redirection system.

## 3. Target User
Human Care Managers operating within a payer or population health organization.

## 4. Payer/Care-Management Context
The solution operates retrospectively or at the point of care-coordination (not point-of-injury). It uses historical claims to find high-risk utilization patterns to proactively navigate members to appropriate lower-acuity care.

## 5. Data Sources
- CMS SynPUF historical claims (Outpatient, Inpatient, Beneficiary).
- Synthetic provider catalog for demo purposes.

## 6. Feature Engineering
Point-in-time features generated strictly from historical events occurring before the prediction date. Aggregations include 90-day rolling windows (e.g., `ed_visits_90d`, `outpatient_visits_90d`). Temporal leakage controls ensure no future information influences past features.

## 7. XGBoost Model
A binary classifier predicting repeat ED-candidate utilization risk within a 90-day window. The output is a risk probability and a derived `risk_band` (HIGH/LOW). It predicts utilization risk, NOT clinical severity or avoidability.

## 8. Safety Gate
A deterministic rule engine that evaluates current clinical context (e.g., vitals, triage notes). It has three final states:
- `POSSIBLE_EMERGENCY` → navigation_allowed = FALSE
- `INSUFFICIENT_INFORMATION` → navigation_allowed = FALSE (requests info)
- `NO_EMERGENCY_INDICATOR` → navigation_allowed = TRUE

## 9. Navigation Opportunity
Distinct from the XGBoost risk model. Evaluates specific historical evidence and assigns an opportunity score and level (e.g., `MEDIUM`). It uses the verbiage `POTENTIAL_NAVIGATION_OPPORTUNITY` and never claims an ED visit was "unnecessary" or "avoidable".

## 10. Driver Analysis
Identifies evidence-based drivers supporting the navigation opportunity (e.g., `HIGH_ED_FREQUENCY` backed by `ed_visits_90d = 4`). The engine does not fabricate clinical diagnoses or preferences when data is unavailable.

## 11. Pathway Recommendation
Recommends lower-acuity pathways (`PRIMARY_CARE`, `URGENT_CARE`, `TELEHEALTH`, `CARE_MANAGEMENT`) based on the Safety Gate, Opportunity, and Drivers, not simply risk scores. Final recommendations always mandate `human_review_required = TRUE`.

## 12. Provider Recommendation
Queries a provider database based on the recommended pathway, state, and telehealth filters. Deterministic ranking is used based on MIPS scores and facility affiliations. Real-time availability and network status are marked as `NOT_VERIFIED` due to prototype limitations.

## 13. Care Manager
A human-in-the-loop review stage. Allowed decisions are `APPROVE`, `MODIFY`, `REJECT`, `ESCALATE`. Any AI recommendation modified by the human preserves the original audit trail alongside the modification.

## 14. Intervention
An authoritative server-side record created only upon Care Manager approval. Validates the `review_id` and implements duplicate protection. Prevents client-side manipulation of final pathways or safety statuses.

## 15. Outcome
Observational measurement comparing a 90-day window following the intervention to a historical index encounter baseline. It tracks repeat ED and outpatient follow-ups. The architecture explicitly does not claim the intervention *prevented* an ED visit, but rather observes the utilization behavior.

## 16. Member History
Operational event logging for `INTERVENTION` and `OUTCOME` occurrences. This repository is kept separate from CMS claims.

## 17. Feedback Loop
Operational member history is persisted and temporally bounded, but direct integration into the current feature-generation pipeline is **future-ready** rather than currently active. A full ML feedback loop retraining the model is not implemented in this prototype.

## 18. Security/Authority Chain
Strict server-side validation. Clients cannot bypass the Safety Gate or manipulate intervention records by submitting spoofed status flags. Session IDs chain the sequence together (`safety_session_id` → `opportunity_session_id` → ... → `review_id`). Reviewer identity is a prototype representation (`reviewer_id` string).

## 19. Temporal Leakage Controls
Historical features for prediction at Date T strictly exclude events occurring after Date T. Future events will only be included in later cycles when they fall inside the proper historical window.

## 20. Limitations
- Provider catalog is synthetic prototype/demo data.
- Reviewer authentication is prototype-level (simple string ID vs. JWT/SSO).
- Real-time appointment availability and network status are unavailable.
- No automatic model retraining.
- Absence of outcome claims does not prove intervention success.
- Future scoring based on Member History is future-ready, not actively queried.
- Dependent on prototype/synthetic CMS claims data.

## 21. Future Production Improvements
- Connect to live HIE/EHR for real-time vitals and context in the Safety Gate.
- Integrate active provider directory with FHIR-based appointment scheduling.
- Implement production SSO/JWT authentication.
- Connect the Member History database to the automated feature engineering pipeline.
- Implement automated model drift detection and retraining pipelines.
