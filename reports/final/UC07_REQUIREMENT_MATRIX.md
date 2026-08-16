| Requirement | Required by UC07? | Existing implementation | File | Status | Evidence |
|---|---|---|---|---|---|
| ED / NON-ED classification | Yes | Deterministic mapping using HCPCS (99281-99285) | `cms_pipeline.py`, `improve_data_investigation.py` | IMPLEMENTED | `ed_candidate_flag`, `ed_classification` logic |
| Repeat ED utilization risk | Yes | Pre-trained ML model (joblib) predicting 90-day repeat visit | `backend/main.py`, `build_kg_rag.py` | IMPLEMENTED | `repeat_ed_risk_model.joblib`, `target_repeat_ed_90d` |
| Potential Navigation Opportunity | Yes | Derived conceptually from risk and historical drivers, but not explicitly decoupled from safety | `backend/main.py` | PARTIALLY_IMPLEMENTED | Endpoint `/v1/pathways` returns pathways for high risk, but it is basic logic |
| Clinical emergency/safety assessment | Yes | Hardcoded fallback for CMS data; Synthea cases have mock status. No real-time assessment engine. | `navigator_api/main.py`, `next_product_layers/generate_pathway_recommendations.py` | PARTIALLY_IMPLEMENTED | Returns `INSUFFICIENT_CURRENT_CLINICAL_DATA` for CMS. |
| Pathway recommendation | Yes | Basic rule-engine routing based on risk score and clinical data existence | `backend/main.py`, `pathway_rules.json` | IMPLEMENTED | `PRIMARY_CARE`, `CARE_MANAGEMENT`, `TELEHEALTH` rules |
| Provider recommendation | Yes | SQLite lookup based on specialty and state, ranking by MIPS | `backend/main.py`, `build_provider_catalog.py` | IMPLEMENTED | `/v1/providers/search` endpoint |
| Human care-manager decision | Yes | System records 'reviewer_cleared' state and final pathway | `backend/main.py` | IMPLEMENTED | `create_intervention` endpoint with `reviewer_cleared` flag |
| Observational Outcome tracking | Yes | Tracks subsequent visits post-intervention | `backend/main.py` | IMPLEMENTED | `/v1/interventions/{id}/outcomes` endpoint |
| Prospective Navigation | Yes | Cannot natively support real-time symptoms without an external intake mechanism | None | MISSING | No symptom/intake processor |
| Deterministic Safety Gate | Yes | Recognized in rules, but no actual engine processes vitals or symptoms | `pathway_rules.json` | MISSING | Hardcoded statuses only |
| RAG Retrieval | Yes | Basic text match over local markdown files for governance rules | `backend/main.py`, `build_kg_rag.py` | IMPLEMENTED | `/v1/rag/search` endpoint, though search is basic keyword matching |
