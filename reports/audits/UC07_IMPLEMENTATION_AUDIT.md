# UC07 Implementation Audit Report

## 1. Executive Summary
The existing codebase implements a robust, retrospective data pipeline and a basic decision-support backend for identifying CMS patients at high risk for repeat Emergency Department (ED) utilization. It adheres to strict principles prohibiting autonomous triage or redirection of emergency care. However, it lacks a real-time prospective intake mechanism and a deterministic safety-gate engine capable of evaluating active clinical symptoms. It correctly treats "repeat ED risk" separately from "avoidability."

## 2. Problem Statement Alignment
The implementation aligns with the core goal of providing decision support for care navigation, rather than autonomous AI triage. It successfully isolates ED identification, model scoring, and pathway recommendation.

## 3. Existing Architecture
The architecture comprises a retrospective data-processing layer (`improve_data_investigation.py`), a local Knowledge Graph (`build_kg_rag.py`) linking patients to drivers, an operational backend (`backend/main.py`) serving the ML model, and a client-facing API (`navigator_api/main.py`). The system is completely dependent on CMS claims data and separate Synthea mock cases.

## 4. Data Pipeline
The data pipeline is highly rigorous. It successfully collapses CMS claim segments by `CLM_ID`, deterministically flags ED utilization via HCPCS codes (99281-99285), and extracts strict point-in-time features (e.g., 30/90-day histories) devoid of data leakage.

## 5. ML Model
The system uses a pre-trained `.joblib` model (likely XGBoost or Calibrated Logistic Regression) that predicts `target_repeat_ed_90d` (the probability of a repeat ED visit in the next 90 days). It correctly does **NOT** attempt to predict "avoidability". 

## 6. ED Identification
ED identification is cleanly decoupled from risk prediction. It relies on deterministic HCPCS logic on historical claims rather than an ML classifier.

## 7. Safety Gate
**MISSING - CRITICAL**. While the logic rules (`pathway_rules.json`) acknowledge that `POSSIBLE_EMERGENCY` overrides risk scores, there is no real-time deterministic engine capable of intaking and evaluating symptoms or vitals. CMS cases currently hardcode to `INSUFFICIENT_CURRENT_CLINICAL_DATA`.

## 8. Navigation Opportunity
Navigation opportunity is partially decoupled. The backend uses the `risk_band` alongside specific utilization drivers (e.g., "no recent outpatient visits") to recommend distinct pathways (like `CARE_MANAGEMENT`), ensuring it does not treat risk scoring as the final answer.

## 9. Driver Analysis
The Knowledge Graph cleanly separates patient IDs from cases and edges them to specific "utilization drivers" (e.g., "No outpatient claim events in the prior 90 days"). The LLM does not hallucinate these; they are deterministically extracted.

## 10. RAG
The RAG system (`/v1/rag/search`) is rudimentary. It uses simple word-intersection matching over local markdown documents. It serves approved guidance to care managers but has no vector DB or advanced LLM reasoning.

## 11. Pathway Recommendation
Implemented via `pathway_rules.json`. It evaluates the safety status and ML risk band to route to `PRIMARY_CARE`, `CARE_MANAGEMENT`, or `TELEHEALTH`. Crucially, if safety data is missing, it routes to `CLINICAL_REVIEW_REQUIRED`.

## 12. Provider Recommendation
Fully implemented using a SQLite database containing CMS provider details. It filters based on pathway requirements (e.g., `PRIMARY_CARE` specialties) and state, ranking deterministically by MIPS score and facility affiliations. 

## 13. Human-in-the-Loop
Strictly adhered to. The system sets `reviewer_cleared = False` by default and endpoints prohibit automated pathway clearance without explicit care-manager overriding.

## 14. Outcome Tracking
Implemented. The `backend/main.py` outcome endpoints calculate observational tracking over 30/90-day windows post-intervention, tracking subsequent ED or outpatient visits without claiming causal attribution.

## 15. Scenario A — Prospective
**MISSING**. The system has no real-time intake mechanism to support prospective patient symptom evaluation.

## 16. Scenario B — At-ED
**IMPLEMENTED**. The rules engine prevents the ML risk score from blocking or clearing current encounters automatically.

## 17. Scenario C — Emergency
**PARTIAL**. Conceptually supported in `pathway_rules.json` (POSSIBLE_EMERGENCY -> STOP), but no active classifier exists to detect an emergency.

## 18. Scenario D — New Patient
**IMPLEMENTED**. Missing clinical data forces a fallback to `INSUFFICIENT_CURRENT_CLINICAL_DATA` requiring human review.

## 19. Scenario E — Historical Member
**IMPLEMENTED**. A historical member is successfully parsed through the risk pipeline to a care management pathway.

## 20. Scenario F — Single ED
**IMPLEMENTED**. The system evaluates longitudinal 90-day risk drivers; one isolated ED visit does not automatically trigger high risk.

## 21. Scenario G — High Utilization but Appropriate
**IMPLEMENTED**. The ML flags high risk, but the recommendation requires Human Care Manager clinical review. The AI does not unilaterally classify it as "avoidable".

## 22. Scenario H — No PCP
**PARTIAL**. Care managers can use `/v1/providers/search` to find a PCP, but the system doesn't natively assess existing PCP attribution.

## 23. Scenario I — Telehealth unavailable
**IMPLEMENTED**. Provider search filters explicitly by `telehealth_available='YES'`.

## 24. Scenario J — Patient rejects
**IMPLEMENTED**. The `/v1/interventions` endpoint records notes and status determined by the care manager.

## 25. Scenario K — Repeat ED
**IMPLEMENTED**. Supported via the retrospective point-in-time calculation pipeline.

## 26. Scenario L — Post-ED
**IMPLEMENTED**. A core operational flow within the CMS data pipeline (evaluating post-index trajectories).

## 27. Agentic AI Architecture
The architecture is rule-based and deterministic. It currently avoids autonomous LLM agency entirely. RAG is used purely for text retrieval.

## 28. Data Leakage Audit
No data leakage was found. `improve_data_investigation.py` calculates all ML features relative to a strict, prior index date window.

## 29. Safety Risks
The highest safety risk is the lack of a real-time clinical evaluation gate to generate the `safety_status`. Relying on mock fallback values in a production environment is unsafe.

## 30. Missing Components
* Real-time patient/symptom intake processor.
* Deterministic real-time safety classification engine.
* Advanced RAG (currently only keyword matching).
* Existing PCP attribution linkage.

## 31. Incorrect Components
The RAG search endpoint (`/v1/rag/search`) uses a basic `set(query.lower().split())` intersection instead of true semantic embedding search, yielding very poor semantic accuracy.

## 32. Partial Components
* Pathway rule execution (basic `if/then` over JSON instead of a robust rule engine).
* Navigation opportunity (not entirely abstracted from the ML model risk band).

## 33. Priority Fix Order
1. Build a deterministic real-time Safety Gate.
2. Implement a prospective intake API for symptoms.
3. Upgrade RAG from keyword matching to a vector-embedding approach.
4. Integrate PCP attribution logic.

## 34. Final UC07 Alignment Score
**PARTIALLY ALIGNED.**
The system accurately aligns with the required retrospective data discipline, ML limitations, and human-in-the-loop constraints. However, it lacks the prospective intake and real-time safety gating required to fully realize the UC07 architecture.
