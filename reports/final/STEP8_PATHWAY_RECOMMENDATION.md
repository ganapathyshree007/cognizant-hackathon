# Step 8: Pathway Recommendation

## 1. Purpose
The Step 8 Pathway Engine deterministically evaluates verified Step 7 drivers and Step 6 opportunity levels to generate a recommended lower-acuity care pathway for human care-manager review. It bridges the gap between identifying "why" a patient was flagged (the drivers) and "where" they might benefit from being navigated.

## 2. Scope
This engine is exclusively for care-navigation decision support. It does **not** provide medical triage, diagnose clinical conditions, or determine if an emergency department visit was "avoidable."

## 3. Inputs
The engine strictly requires server-verified state:
- `opportunity_level` (from Step 6, via the session chain)
- `drivers` (from Step 7, via the session chain)
- `telehealth_preferred` (contextual client preference, used only if navigation is already clinically supported)

## 4. Safety Gate Dependency
Pathway recommendations cannot execute unless the initial Step 5 Safety Gate explicitly cleared the case with `NO_EMERGENCY_INDICATOR`. If `POSSIBLE_EMERGENCY` or `INSUFFICIENT_INFORMATION` is detected anywhere in the session chain, the recommendation is blocked.

## 5. Step 6 Dependency
The engine requires a minimum `opportunity_level` of `MEDIUM` or `HIGH` to recommend any specific care pathway. Low opportunity scores trigger a fallback `NO_PATHWAY_RECOMMENDATION` state.

## 6. Step 7 Dependency
Candidate pathways are generated directly from specific verified `driver_id` tokens (e.g., `LOW_OUTPATIENT_ENGAGEMENT` triggers a `PRIMARY_CARE` candidacy).

## 7. Allowed Pathways
The engine supports the following pathways:
- `PRIMARY_CARE`
- `URGENT_CARE`
- `TELEHEALTH`
- `CARE_MANAGEMENT`
- `NO_PATHWAY_RECOMMENDATION` (fallback)

## 8. Candidate Generation
Candidates are generated through deterministic matching:
- **Primary Care**: Supported by `LOW_OUTPATIENT_ENGAGEMENT`.
- **Urgent Care**: Supported by `RECENT_ED_UTILIZATION` (without high inpatient complexity).
- **Care Management**: Supported strictly by `CARE_COORDINATION_GAP`.
- **Telehealth**: Supported as a candidate *only* if the patient is already eligible for another lower-acuity pathway and `telehealth_preferred` is True.

## 9. Ranking Methodology
When multiple candidate pathways are generated, they are deterministically ranked according to an internal priority array:
`[CARE_MANAGEMENT, PRIMARY_CARE, TELEHEALTH, URGENT_CARE]`
The top result is the `recommended_pathway`, while the rest are provided as `alternative_pathways`.

## 10. Explainability
The endpoint provides a rich JSON response that includes a human-readable `reason` and lists the specific `supporting_drivers` that triggered the recommendation.

## 11. Human Review
All output pathways are explicitly flagged with `human_review_required: true`. The API returns a `status` of `CARE_MANAGER_REVIEW` rather than automatically routing the patient.

## 12. LLM/RAG Boundary
Pathway ranking is **100% deterministic**. No Large Language Model or generative AI is permitted to choose the pathway. RAG systems may be used in future steps solely to display documentation supporting this deterministic decision.

## 13. Avoidability Limitation
The engine is explicitly forbidden from claiming an ED visit was avoidable. High utilization context (e.g., high inpatient visits) is treated as complexity preventing automated primary care routing, rather than an avoidability care gap.

## 14. Provider Handoff to Step 9
Step 8 recommends a pathway *category* (e.g., `PRIMARY_CARE`). The actual selection of a specific physician or facility is left to Step 9 (Provider Search), which filters available specialties based on this category.

## 15. Rule Versioning
All decisions include a `rule_version` string (e.g., `PATHWAY_RULES_V1`) to track the deterministic logic applied at the time of the recommendation.

## 16. Testing
`test_step8_pathways.py` exhaustively tests candidate generation, safety blocking, single-visit logic, client manipulation attempts, and historical leakage protections.

## 17. Known Limitations
The synthetic dataset lacks deep care-management features, limiting the nuance of the `CARE_COORDINATION_GAP` detection compared to a production clinical pipeline.
