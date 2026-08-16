# Safety Gate Documentation

## 1. Purpose
The Safety Gate provides a conservative, deterministic decision-support screen to ensure patients with potential emergency conditions are not automatically navigated to lower-acuity pathways. It is **not** a substitute for professional medical assessment, emergency services, clinical triage, diagnosis, or treatment.

## 2. Architecture Position
The Safety Gate sits between the raw encounter identification and the Navigation Opportunity engine. It intercepts the workflow, demanding sufficient active clinical context before historical data is permitted to influence downstream navigation.

## 3. Safety States
- **POSSIBLE_EMERGENCY**: A critical indicator triggered an emergency rule.
- **INSUFFICIENT_INFORMATION**: The system lacks actionable current clinical data (like vitals or clinician assessment).
- **NO_EMERGENCY_INDICATOR**: Sufficient data exists and no emergency rules were triggered.

## 4. Information-Request Workflow
When data is insufficient, the system returns `action_required: "REQUEST_INFORMATION"`. It lists missing parameters. Automated navigation halts until satisfied.

## 5. Reassessment Workflow
Upon receiving new information, the Safety Gate merges it with the existing session context and deterministically re-evaluates. 

## 6. Emergency Handling
If a possible emergency is detected, automated navigation is immediately aborted (`action_required: "STOP_NAVIGATION"`, `human_review_required: true`). The patient is **never** redirected from the ED.

## 7. Missing-Information Handling
Missing information is never treated as safe. It results in a request for info.

## 8. Human-Review Handling
If the system requests information but reaches the maximum attempts limit (default: 2), it defaults to escalation: `HUMAN_CLINICAL_REVIEW`. No automated decisions will proceed.

## 9. Rule Definitions
*(For the current prototype, no autonomous triage thresholds like NEWS2 are enabled against real claims data due to lacking context. Rule tests are restricted to synthetic test fixtures specifically to validate the rules engine mechanics.)*

## 10. Clinical Sources
No independent triage thresholds are currently active. Test fixtures are used purely for engine validation.

## 11. Rule Versioning
Version: 1.0.0 (Test-Fixture Support Only).

## 12. API Integration
Exposed via `POST /v1/safety/assess`. See `backend/main.py`.

## 13. Testing
Automated testing is maintained in `test_safety_gate.py`.

## 14. Limitations
The Safety Gate is a conservative decision-support screening mechanism. It is not a substitute for professional medical assessment, emergency services, clinical triage, diagnosis, or treatment. It cannot guarantee a patient is safe from a medical emergency.
