# UC07 FINAL END-TO-END TRACE

This document traces one real executable scenario through the actual backend APIs, recording the input, model/method, database, output, and data flow at each stage.

## Scenario Features
- `ed_visits_90d`: 4
- `outpatient_visits_90d`: 0
- `inpatient_visits_90d`: 1
- `age`: 67

---

### [1] FEATURES → XGBoost
1. **API/endpoint**: `POST /v1/score`
2. **Input**: `{"features": {"ed_visits_90d": 4, "outpatient_visits_90d": 0, "inpatient_visits_90d": 1, "age": 67}}`
3. **Model/method**: XGBoost binary classifier (`predict_proba`)
4. **Database/session**: Stateless prediction
5. **Output**: 
   ```json
   {
     "risk_score": 0.85,
     "risk_band": "HIGH",
     "threshold": 0.5,
     "target": "repeat ED-candidate utilization within 90 days",
     "notice": "Decision support only; not avoidability or clinical triage."
   }
   ```
6. **Next Step**: The `risk_score` is a general context. However, it does NOT automatically trigger navigation.

---

### [2] XGBoost → Safety Gate
1. **API/endpoint**: `POST /v1/safety/assess`
2. **Input**: `{"case_id": "case-123", "patient_id": "member-123", "new_context": {"triage_notes": "...", "vitals": "...", "clinician_assessment": "..."}}`
3. **Model/method**: Deterministic rule engine (`evaluate_safety`)
4. **Database/session**: `safety_sessions` table (creates a `session_id`)
5. **Output**:
   ```json
   {
     "session_id": "a1955424-d3e6-4f79-a6c0-8ea8a2acb54c",
     "safety_status": "NO_EMERGENCY_INDICATOR",
     "navigation_allowed": true,
     "human_review_required": false,
     "action_required": "CONTINUE_NAVIGATION",
     "reason": "Information sufficient and no emergency rule triggered."
   }
   ```
6. **Next Step**: The resulting `session_id` and `safety_status` are passed to the Navigation Opportunity engine.

---

### [3] Safety Gate → Navigation Opportunity
1. **API/endpoint**: `POST /v1/navigation-opportunity`
2. **Input**: `{"case_id": "case-123", "safety_session_id": "a1955424-d3e6-4f79-a6c0-8ea8a2acb54c"}`
3. **Model/method**: Point-based rule engine (`calculate_opportunity`)
4. **Database/session**: `opportunity_sessions` table
5. **Output**:
   ```json
   {
     "opportunity_id": "02a7fb65-a761-44fa-b89b-20547bdf0709",
     "navigation_allowed": true,
     "navigation_opportunity_score": 60,
     "navigation_opportunity_level": "MEDIUM",
     "drivers": ["HIGH_RECENT_ED_UTILIZATION", "LOW_OUTPATIENT_UTILIZATION"]
   }
   ```
6. **Next Step**: The `opportunity_id` is passed to the Driver Analysis engine to resolve the evidence for these drivers.

---

### [4] Opportunity → Driver Analysis
1. **API/endpoint**: `POST /v1/drivers/analyze`
2. **Input**: `{"case_id": "case-123", "opportunity_session_id": "02a7fb65-a761-44fa-b89b-20547bdf0709"}`
3. **Model/method**: Driver matching using `kg_case` and local rules
4. **Database/session**: `driver_sessions` table
5. **Output**:
   ```json
   {
     "driver_session_id": "f207d824-80f3-4ac7-b2f9-30951090f758",
     "driver_status": "SUPPORTED_EVIDENCE",
     "drivers": [
       {"driver_id": "HIGH_ED_FREQUENCY", "evidence": {"ed_visits_90d": 4}, "strength": "HIGH"},
       {"driver_id": "LOW_OUTPATIENT_ENGAGEMENT", "evidence": {"outpatient_visits_90d": 0}, "strength": "HIGH"}
     ]
   }
   ```
6. **Next Step**: The `driver_session_id` is passed to the Pathway Recommendation engine.

---

### [5] Drivers → Pathway Recommendation
1. **API/endpoint**: `POST /v1/pathways/recommend`
2. **Input**: `{"case_id": "case-123", "reviewer_id": "reviewer-1", "driver_session_id": "f207d824-80f3-4ac7-b2f9-30951090f758"}`
3. **Model/method**: Rule-based pathway mapper (evaluating specific combinations of drivers)
4. **Database/session**: `pathway_sessions` table
5. **Output**:
   ```json
   {
     "pathway_session_id": "635819f9-d854-4b49-8929-b556dcaa1a36",
     "recommended_pathway": "PRIMARY_CARE",
     "human_review_required": true
   }
   ```
6. **Next Step**: The `pathway_session_id` and the `recommended_pathway` are used to search for providers.

---

### [6] Pathway → Provider Recommendation
1. **API/endpoint**: `POST /v1/providers/recommend`
2. **Input**: `{"pathway_session_id": "635819f9-d854-4b49-8929-b556dcaa1a36"}`
3. **Model/method**: Deterministic SQL query matching on `provider_catalog.sqlite`
4. **Database/session**: `provider_sessions` table
5. **Output**:
   ```json
   {
     "provider_session_id": "08062c31-5ea8-47a7-a606-888a028479cd",
     "provider_results": [{"provider_name": "Demo Telehealth Doc", "specialty": "INTERNAL MEDICINE"}]
   }
   ```
6. **Next Step**: The `provider_session_id` is passed to the Care Manager for Human-in-the-Loop review.

---

### [7] Provider → Care Manager Review
1. **API/endpoint**: `POST /v1/care-manager/review`
2. **Input**: `{"provider_session_id": "08062c31-5ea8-47a7-a606-888a028479cd", "reviewer_id": "reviewer-1", "decision": "APPROVE"}`
3. **Model/method**: Human-in-the-Loop server-side validation
4. **Database/session**: `care_manager_reviews` table
5. **Output**:
   ```json
   {
     "review_id": "4453b6ad-86e7-4f1f-bf20-d9d45190b233",
     "status": "APPROVE"
   }
   ```
6. **Next Step**: The approved `review_id` enables the Intervention to be recorded.

---

### [8] Care Manager → Intervention
1. **API/endpoint**: `POST /v1/interventions`
2. **Input**: `{"review_id": "4453b6ad-86e7-4f1f-bf20-d9d45190b233"}`
3. **Model/method**: Database record insertion with idempotency checks
4. **Database/session**: `interventions` and `member_history` tables
5. **Output**:
   ```json
   {
     "intervention_id": "1d487618-eaf1-4f8d-86cd-862bde7c0b97",
     "status": "REVIEWED"
   }
   ```
6. **Next Step**: The `intervention_id` is the anchor for measuring later outcomes.

---

### [9] Intervention → Outcome
1. **API/endpoint**: `POST /v1/outcomes`
2. **Input**: `{"intervention_id": "1d487618-eaf1-4f8d-86cd-862bde7c0b97"}`
3. **Model/method**: 90-day observation window comparison against historical claims
4. **Database/session**: `outcomes` and `member_history` tables
5. **Output**:
   ```json
   {
     "outcomes": {
       "INDEX_ENCOUNTER": {"anchor_date": "2023-01-01", "repeat_ed": 0},
       "POST_INTERVENTION": {"anchor_date": "2026-08-14", "repeat_ed": 0}
     }
   }
   ```
6. **Next Step**: The outcome and intervention events are persisted in `member_history`.

---

### [10] Outcome → Member History
**Observation**: The system inserts `INTERVENTION` and `OUTCOME` event types into the local `member_history` operational table. This is separate from CMS claims.
**Database output**:
```
EVENT: INTERVENTION | DATE: 2026-08-14T15:15:44.470597+00:00 | SOURCE: intervention_id:1d487618-eaf1-4f8d-86cd-862bde7c0b97 | DETAILS: {"review_id": "4453b6ad-86e7-4f1f-bf20-d9d45190b233", "decision": "APPROVE"}
EVENT: OUTCOME | DATE: 2026-08-14T15:15:44.470597 | SOURCE: outcome_id:aaa11e11-ab24-4a8d-aa98-ad6ec54151fe | DETAILS: {"repeat_ed": 0, "outpatient_followup": 0, "inpatient_event": 0}
```
**Future Loop**: This historical table is explicitly future-ready. In a production pipeline, feature generation queries this database to include past care-management engagements as predictive features.
