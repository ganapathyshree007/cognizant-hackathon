# Step 8: Pathway Recommendation Audit

## A. Current Pathway Selection
Currently, `POST /v1/pathways` handles pathway selection directly inside the endpoint using basic, hardcoded `if/else` rules based on `telehealth_preferred`, `opp_level`, and a single driver (`LOW_OUTPATIENT_ENGAGEMENT`). It returns a single string rather than a structured object with candidates, rationale, and alternatives.

## B. Client Input Trust
The endpoint retrieves historical context safely via the `driver_session_id` chain. It correctly does *not* trust client overrides for opportunity scores, driver arrays, or safety statuses. It does accept `telehealth_preferred` and `reviewer_cleared` from the client request.

## C. Risk Band Control
The `risk_band` (Step 4) no longer directly controls pathways. It was decoupled during Step 6, closing that bypass.

## D. Navigation Opportunity Level
Yes, the `navigation_opportunity_level` (`opp_level`) is used as an input to the current pathway logic.

## E. Step 7 Drivers Use
Yes, the current endpoint parses the stored JSON drivers from the `driver_sessions` table and queries specific strings (`LOW_OUTPATIENT_ENGAGEMENT`) to influence routing.

## F. Safety Gate Enforcement
Yes, the Safety Gate is fully enforced. The endpoint fetches the `safety_session` via the session chain and blocks pathway generation if the status is anything other than `NO_EMERGENCY_INDICATOR`.

## G. Provider Recommendation Dependency
Yes, the existing `provider_search` function explicitly filters specialties based on the `pathway` parameter (`PRIMARY_CARE`, `TELEHEALTH`, `CARE_MANAGEMENT`, `URGENT_CARE`).

## H. LLM / RAG Influence
LLMs and RAG do not currently influence pathway selection. It is deterministic Python logic.

## I. Unsupported Pathway Submission
The client cannot submit a custom pathway because `PathwayRequest` does not accept a pathway parameter; the server exclusively calculates and returns it.

## J. Determinism
Pathway decisions are currently 100% deterministic and reproducible based on the server-side session data.
