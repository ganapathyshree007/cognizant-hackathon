# Step 10: Care Manager / Human-in-the-Loop

## 1. Purpose
The Step 10 Care Manager Review layer enforces mandatory human oversight before any care navigation intervention can occur. It prevents the system from automatically converting AI recommendations (such as ML-predicted risk scores and deterministically matched provider directories) into patient actions.

## 2. Human-in-the-loop Architecture
The Care Manager Review layer completely isolates the automated AI pipeline (Steps 1–9) from the final intervention.
The client retrieves a read-only `Care Manager Context` using a verified `provider_session_id`.
The Care Manager must then submit an explicit decision (`APPROVE`, `MODIFY`, `REJECT`, or `ESCALATE`) via `POST /v1/care-manager/review`.
Only an `APPROVE` or `MODIFY` decision will unlock the ability to post to `/v1/interventions`.

## 3. Review States
- **APPROVE**: Accepts the AI-recommended pathway and provider options exactly as presented.
- **MODIFY**: Overrides the AI's recommendation (e.g., changing from `PRIMARY_CARE` to `TELEHEALTH`), substituting human clinical judgment.
- **REJECT**: Completely halts the lower-acuity navigation attempt. No intervention is created.
- **ESCALATE**: Halts the lower-acuity navigation attempt and flags the case for higher-level clinical review.

## 4. Approval Workflow
When the Care Manager selects `APPROVE`, the system captures their `reviewer_id`, a timestamp, and exactly copies the `original_pathway` into the final review record. This record is then used to safely create the intervention.

## 5. Modification Workflow
If a human modifies the recommendation, the system strictly preserves the **original AI recommendation** alongside the **human modified decision**. The AI's original recommendation is never overwritten. The modified pathway becomes the final authoritative decision sent to the intervention log.

## 6. Rejection Workflow
If the case is rejected, the API creates a review record with `decision = 'REJECT'` but permanently blocks the creation of any subsequent navigation intervention.

## 7. Escalation Workflow
If the case is escalated, the API records the `ESCALATE` decision and blocks lower-acuity interventions, effectively routing the case away from standard automated navigation flows into specialized clinical review channels.

## 8. Server Authority
The client UI cannot submit arbitrary text to define the AI's recommendation. The server strictly retrieves the recommendation from the upstream `provider_session_id` and ignores any attempt to spoof the `original_pathway` or `safety_status`.

## 9. Session Chain
The backend validates the exact lineage of the recommendation:
`provider_session_id` → `pathway_session_id` → `driver_session_id` → `opportunity_session_id` → `safety_session_id`.
If any link in the chain is invalid or mismatched to the patient case, the review is blocked.

## 10. Safety Gate Interaction
The backend enforces the authoritative Safety Gate (Step 5) natively. If the `safety_session` flagged the case as `POSSIBLE_EMERGENCY` or `INSUFFICIENT_INFORMATION`, the backend blocks the creation of lower-acuity interventions (preventing dangerous diversions). The case may still be presented to the appropriate human/clinical reviewer for review and escalation, but no standard navigation intervention can proceed.

## 11. Intervention Boundary
The `POST /v1/interventions` API no longer accepts raw client input to determine safety or pathway details. It exclusively requires a valid `review_id` that maps to an `APPROVE` or `MODIFY` care manager decision.

## 12. Audit Trail
All reviews are persisted in the `care_manager_reviews` table. This audit trail captures:
- `review_id`
- `case_id`
- `reviewer_id`
- The human decision
- Both the original AI recommendation and the human modification
- Review timestamps

## 13. Authentication Limitations
**Prototype Limitation**: Do not treat a client-supplied `reviewer_id` as authenticated identity. Since full authentication is unavailable in this prototype (beyond simple API keys), this is clearly documented as a limitation. Production must derive identity from an authenticated session to prevent spoofing.

## 14. Known Limitations
- Modifying a specific provider choice is partially supported via `modified_provider_id`, but complex provider search UI flows during modification are out of scope for the backend API prototype.
