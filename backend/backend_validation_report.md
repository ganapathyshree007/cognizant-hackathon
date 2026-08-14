# UC07 backend architecture validation

## Model target — PASS

The saved XGBoost model predicts **repeat ED-candidate utilization within 90 days strictly after an index ED day**. It does not predict avoidability, diagnosis, safety, or pathway eligibility. Model inputs exclude IDs, dates, target fields, split fields, and index year.

## Safety separation — PASS, with boundary noted

`/v1/score` returns only utilization risk. `/v1/pathways` requires an independently supplied safety status and reviewer clearance. `POSSIBLE_EMERGENCY`, `INSUFFICIENT_CLINICAL_DATA`, and `CLINICAL_REVIEW_REQUIRED` always stop automated pathway assignment. CMS case retrieval defaults to insufficient current clinical data because it has no real-time clinical evidence.

## Outcome windows — PASS

The claims filter is strictly `start_date > anchor_date`, so it excludes the index day itself. A known positive case (`1E84B45C6F1C6334`, index 2010-01-01) has a later ED event on 2010-02-03 within 90 days, confirming the subsequent-event logic.

The backend now calculates and persists two separate outcomes for every requested 30/90/180-day window: `INDEX_ENCOUNTER` (anchored on the model-case index date) and `POST_INTERVENTION` (anchored on recorded review/intervention time). These are intentionally not conflated.

## Provider retrieval — PASS

The operational API exposes `/v1/providers/search`; it queries the indexed SQLite provider catalog with pathway, state, telehealth, and result-limit controls.

## RAG — PARTIAL PASS

The backend retrieves only documents with `approved_for_retrieval=true`. The current retrievable content is governance material; no approved clinical/navigation protocol has been ingested yet.

## Persistence and audit — PASS

Intervention and outcome records persist in `backend_state.sqlite`. An authenticated HTTP provider-search request returned two records and increased the audit-event count from 0 to 1.

## Verdict

The backend is a **strong operational prototype**, not yet production-ready. The remaining work is production hardening: managed secrets/identity, real data validation, monitoring, clinical governance, and organization approval.
