# Step 10: Care Manager / Human-in-the-Loop Audit

## 1. Executive Summary
The current Step 10 implementation is an unvalidated endpoint (`POST /v1/interventions`) that acts merely as a data sink. It blindly trusts the client for all data, including safety status and the final pathway. It is completely disconnected from the rigorous, server-authoritative session chain established in Steps 5-9. This allows a client to potentially automate interventions, bypass the Safety Gate, and manipulate the clinical record without actual human review.

## 2. Existing Care Manager Architecture
The architecture consists of a simple SQLite table (`interventions`) and three endpoints in `backend/main.py`. There is no actual state machine or enforcement of human review.

## 3. Existing APIs
- `POST /v1/interventions`: Creates an intervention. Blindly trusts client payload.
- `GET /v1/interventions/{intervention_id}`: Retrieves the intervention.
- `POST /v1/interventions/{intervention_id}/outcomes`: Calculates observational claims outcomes relative to the intervention date.

## 4. Human Review Mapping
- **Approve supported:** NO (implied by string matching, but not enforced).
- **Modify supported:** NO (the original AI recommendation is not linked, so it is impossible to audit if it was modified).
- **Reject supported:** NO.
- **Escalate supported:** NO.

## 5. Decision States
The API defaults to `status='REVIEWED'` but accepts any arbitrary string. There are no strict states for APPROVE, MODIFY, REJECT, or ESCALATE.

## 6. Server-Side Authority
**Critically Failed**. The API accepts raw strings for `safety_status` and `final_pathway` without requiring a `provider_session_id` or `pathway_session_id`. The client is completely trusted.

## 7. Reviewer Identity
The `reviewer_id` is a raw string submitted by the client. It is not verified against any authentication system (beyond the global API key).

## 8. Auditability
**Partially Implemented**. The system records timestamps, reviewer_id, case_id, and final_pathway. However, because it does not link to the original `pathway_session_id` or `provider_session_id`, the system cannot audit *what* the AI originally recommended vs *what* the human finally decided.

## 9. Modification Handling
**Missing**. The original recommendation is lost because the session IDs are not linked.

## 10. Rejection Handling
**Missing**. No explicit state exists to block an intervention based on a rejection.

## 11. Escalation Handling
**Missing**. No escalation routing exists.

## 12. Intervention Boundary
**Critically Failed**. Because the API requires no proof of human interaction (e.g., matching a session and a specific human decision enum), a client script could automatically read Step 9 and instantly POST to `/v1/interventions`, resulting in an autonomous AI intervention.

## 13. Safety Gate Integration
**Critically Failed**. The client can simply send `safety_status="NO_EMERGENCY_INDICATOR"` in the payload, entirely bypassing the actual server-side Safety Gate evaluation.

## 14. Provider Integration
**Missing**. The intervention API does not record or accept a `provider_session_id` or `selected_provider`. It only records `final_pathway`.

## 15. LLM/RAG Boundary
**Passed**. RAG is confined to `GET /v1/rag/search` and does not make intervention decisions.

## 16. Test Results
There are no automated tests for the human-in-the-loop workflow protecting against client manipulation.

## 17. Missing Components
- Linkage to `provider_session_id` and `pathway_session_id`.
- Strict human decision states (APPROVE, MODIFY, REJECT, ESCALATE).
- Server-side Safety Gate enforcement.
- Recording of the selected provider.

## 18. Incorrect Components
- The API blindly trusts client-supplied safety statuses and pathways.

## 19. Recommended Changes
1. Update `InterventionRequest` to require `provider_session_id`.
2. Retrieve the full chain (Provider -> Pathway -> Driver -> Opportunity -> Safety) server-side and verify the `safety_status`.
3. Add a strict `decision` enum (APPROVE, MODIFY, REJECT, ESCALATE).
4. Persist the `provider_session_id` to allow auditing of the AI recommendation vs the human decision.

## 20. Priority Order
1. Server-side authority & Session linkage.
2. Safety Gate enforcement on interventions.
3. Strict decision states (Approve/Modify/Reject/Escalate).
4. Capturing the selected provider.
