# UC07 DEMO SCENARIO

## Scenario 1: Standard Navigation Flow

**Features**:
- `ed_visits_90d` = 4
- `outpatient_visits_90d` = 0
- `inpatient_visits_90d` = 1
- `age` = 67

### XGBoost Risk Score
```json
{
  "risk_score": 0.85,
  "risk_band": "HIGH",
  "threshold": 0.5,
  "target": "repeat ED-candidate utilization within 90 days",
  "notice": "Decision support only; not avoidability or clinical triage."
}
```

### Safety Gate
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

### Navigation Opportunity
```json
{
  "opportunity_id": "02a7fb65-a761-44fa-b89b-20547bdf0709",
  "safety_status": "NO_EMERGENCY_INDICATOR",
  "navigation_allowed": true,
  "navigation_opportunity_score": 60,
  "navigation_opportunity_level": "MEDIUM",
  "evidence": {
    "ed_visits_90d": 4,
    "outpatient_visits_90d": 0,
    "inpatient_visits_90d": 1,
    "pcp_engagement": "DATA_UNAVAILABLE"
  },
  "drivers": [
    "HIGH_RECENT_ED_UTILIZATION",
    "LOW_OUTPATIENT_UTILIZATION"
  ],
  "reason": "Calculated prototype score 60/100 based on server-derived historical evidence.",
  "score_version": "NAV_OPP_V1"
}
```

### Driver Analysis
```json
{
  "driver_session_id": "f207d824-80f3-4ac7-b2f9-30951090f758",
  "driver_status": "SUPPORTED_EVIDENCE",
  "drivers": [
    {
      "driver_id": "HIGH_ED_FREQUENCY",
      "driver_name": "High ED utilization",
      "evidence": {
        "ed_visits_90d": 4
      },
      "source": "point_in_time_features",
      "strength": "HIGH"
    },
    {
      "driver_id": "LOW_OUTPATIENT_ENGAGEMENT",
      "driver_name": "Low outpatient engagement",
      "evidence": {
        "outpatient_visits_90d": 0
      },
      "source": "point_in_time_features",
      "strength": "HIGH"
    }
  ],
  "summary": "Identified 2 supporting drivers for navigation opportunity.",
  "avoidability_claim": false
}
```

### Pathway Recommendation
```json
{
  "pathway_session_id": "635819f9-d854-4b49-8929-b556dcaa1a36",
  "status": "CARE_MANAGER_REVIEW",
  "recommended_pathway": "PRIMARY_CARE",
  "alternative_pathways": [],
  "reason": "Recommendation generated based on navigation drivers: HIGH_ED_FREQUENCY, LOW_OUTPATIENT_ENGAGEMENT.",
  "supporting_drivers": [
    "HIGH_ED_FREQUENCY",
    "LOW_OUTPATIENT_ENGAGEMENT"
  ],
  "human_review_required": true,
  "rule_version": "PATHWAY_RULES_V1"
}
```

### Provider Recommendation
```json
{
  "provider_session_id": "08062c31-5ea8-47a7-a606-888a028479cd",
  "pathway_session_id": "635819f9-d854-4b49-8929-b556dcaa1a36",
  "recommended_pathway": "PRIMARY_CARE",
  "provider_results": [
    {
      "specialty": "INTERNAL MEDICINE",
      "telehealth_available": "YES",
      "phone": "555-0103",
      "facility_name": "",
      "provider_name": "Demo Telehealth Doc",
      "facility_id": null,
      "provider_id": "3333333333",
      "location": "San Francisco, CA 94105"
    },
    {
      "specialty": "FAMILY PRACTICE",
      "telehealth_available": "NO",
      "phone": "555-0101",
      "facility_name": "Clinic",
      "provider_name": "Demo Primary Care",
      "facility_id": null,
      "provider_id": "1111111111",
      "location": "San Francisco, CA 94105"
    }
  ],
  "availability_status": "NOT_VERIFIED",
  "network_status": "NOT_VERIFIED",
  "source": "VERIFIED_PROVIDER_DATABASE",
  "human_review_required": true,
  "notice": "Directory options only; verify network, availability, accessibility and clinical fit. The generated provider_catalog.sqlite is synthetic prototype/demo data only. It must never be represented as real provider data, real availability, or real network participation."
}
```

### Care Manager Review
```json
{
  "review_id": "4453b6ad-86e7-4f1f-bf20-d9d45190b233",
  "status": "APPROVE"
}
```

### Intervention
```json
{
  "intervention_id": "1d487618-eaf1-4f8d-86cd-862bde7c0b97",
  "status": "REVIEWED"
}
```

### Outcome
```json
{
  "window_days": 90,
  "outcomes": {
    "INDEX_ENCOUNTER": {
      "outcome_id": "2973cd14-b2a7-4ce4-b9eb-2d0df68e29fc",
      "anchor_date": "2023-01-01",
      "repeat_ed": 0,
      "outpatient_followup": 0,
      "inpatient_event": 0
    },
    "POST_INTERVENTION": {
      "outcome_id": "aaa11e11-ab24-4a8d-aa98-ad6ec54151fe",
      "anchor_date": "2026-08-14",
      "repeat_ed": 0,
      "outpatient_followup": 0,
      "inpatient_event": 0
    }
  },
  "notice": "Index outcomes measure subsequent utilization; post-intervention outcomes measure follow-up after the recorded intervention. Claims absence is not proof of success."
}
```

---

## Scenario 2: Emergency Protection Flow

This scenario demonstrates the critical safety property where an emergency indicator explicitly halts automated lower-acuity navigation.

### Safety Gate (Emergency Condition)
**Context**: "HR 130, BP 80/50, Patient reports severe chest pain and shortness of breath. Possible acute myocardial infarction."

```json
{
  "session_id": "ef86fcef-e8b2-447e-bd22-a84698b27340",
  "safety_status": "POSSIBLE_EMERGENCY",
  "navigation_allowed": false,
  "human_review_required": true,
  "action_required": "STOP_NAVIGATION",
  "triggered_rules": [
    {
      "rule_id": "TEST_FIXTURE_EMERGENCY",
      "evidence": "Explicit test fixture trigger provided.",
      "source": "Synthetic Test Fixture"
    }
  ],
  "reason": "One or more safety rules triggered. Stop automated navigation."
}
```

### Navigation Opportunity (Blocked)
An attempt to query the Navigation Opportunity engine using the above safety session ID results in a hard failure (HTTP 400), proving that lower-acuity diversion is safely prevented.

```json
{
  "detail": "Safety status blocks navigation opportunity evaluation."
}
```
