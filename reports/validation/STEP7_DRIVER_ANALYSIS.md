# Step 7: Driver / Reason Analysis

## 1. Purpose
The Step 7 Driver Engine determines the *reasons* (drivers) a member was flagged for potential care navigation. It provides transparent, explainable context by evaluating point-in-time historical data.

## 2. Relationship to Step 6
Step 6 answers "Is there a potential navigation opportunity?" by generating an opportunity score and level. Step 7 takes that finding and answers "Why?" by breaking it down into specific structured drivers (e.g., `LOW_OUTPATIENT_ENGAGEMENT`). The API ensures Step 7 cannot execute unless a valid Step 6 `opportunity_session_id` is supplied.

## 3. Driver Definitions
- `HIGH_ED_FREQUENCY`: The member has 3 or more ED visits in the historical window.
- `REPEATED_ED_UTILIZATION`: The member has exactly 2 ED visits in the historical window.
- `RECENT_ED_UTILIZATION`: The most recent ED visit was within 14 days.
- `LOW_OUTPATIENT_ENGAGEMENT`: The member has 0 outpatient visits in the historical window.
- `HIGH_INPATIENT_UTILIZATION`: The member has 2 or more inpatient visits, treated strictly as contextual complexity evidence (not as an avoidability care gap).

## 4. Evidence Sources
Drivers are generated deterministically based entirely on pre-calculated point-in-time features from the CMS model data (extracted via the `kg_case()` graph query), specifically:
- `ed_visits_90d`
- `ed_visits_365d`
- `outpatient_visits_90d`
- `inpatient_visits_90d`
- `days_since_latest_ed`

## 5. Temporal Leakage Controls
The engine receives features that were explicitly engineered using data strictly *before* the index date. Step 7 does not have access to future claims, interventions, or subsequent utilization, guaranteeing point-in-time analytical safety.

## 6. Driver Prioritization
Drivers are generated based on deterministic thresholds, and each driver is assigned a `strength` attribute (`HIGH`, `MEDIUM`, `LOW`) depending on the magnitude of the signal in the historical data.

## 7. Insufficient Data Behavior
If the structured data does not trigger any specific drivers, the engine returns `INSUFFICIENT_EVIDENCE`. It explicitly refuses to guess or hypothesize missing patterns.

## 8. LLM / RAG Boundary
Step 7 is **100% deterministic code**. LLMs are structurally prohibited from inventing drivers or creating unsupported clinical evidence. Any future RAG system is permitted only to query and explain these deterministic drivers, not to evaluate the patient data and hallucinate new reasons.

## 9. Knowledge Graph Integration
The engine draws its input features directly from the Knowledge Graph SQLite (`evidence_graph.sqlite`) via `kg_case()`. Future development could extend the Graph to store these generated drivers as node edges for offline analytics.

## 10. API Contract
- **Endpoint**: `POST /v1/navigation-drivers`
- **Requires**: `case_id`, `opportunity_session_id`
- **Returns**: `driver_session_id`, `driver_status`, `drivers` (JSON array), and `summary`.

## 11. Security / Authority Model
The engine enforces a rigid server-side chain of custody:
1. `safety_session_id` (NO_EMERGENCY_INDICATOR required)
2. `opportunity_session_id` (must reference the correct safety_session_id)
3. `driver_session_id` (must reference the correct opportunity_session_id)
The client cannot spoof or bypass these stages.

## 12. Testing
`test_step7_drivers.py` contains 15 explicit test scenarios including single-visit protection, missing data handling, leakage simulation, and client manipulation attempts.

## 13. Limitations
Missing features (like reliable PCP attribution or nuanced sub-specialty data in the CMS synthetic files) limit the ability to create drivers involving chronic-care coordination gaps.

## 14. Why Driver Analysis Does Not Establish Avoidability
The driver analysis is an identification of *utilization patterns*. Emitting a `HIGH_ED_FREQUENCY` driver combined with `HIGH_INPATIENT_UTILIZATION` establishes that the patient uses the healthcare system frequently; it does **not** make a clinical judgment that their ED visit was an avoidable error or that they should have stayed home.
