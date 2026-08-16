"""
Step 6 Navigation Opportunity Engine.

The Navigation Opportunity Score is a transparent prototype
decision-support score based on historical utilization evidence.
It is not a clinically validated score and does not establish that
an ED visit was avoidable or inappropriate.

It calculates a heuristic score (0-100) to separate ED risk from 
lower-acuity navigation opportunity.
"""
from typing import Dict, Any, List, Tuple

def calculate_opportunity(features: Dict[str, Any]) -> Dict[str, Any]:
    score = 0
    drivers = []
    evidence = {}
    
    # 1. Base score from Repeat ED Risk (if available in features)
    risk_score = features.get('risk_score', 0.0)
    if risk_score > 0:
        base_points = min(40, int(risk_score * 40))
        score += base_points
        evidence['repeat_ed_risk_score'] = risk_score
        
    # 2. ED Utilization Pattern
    ed_90 = features.get('ed_visits_90d', features.get('ed_visits_365d', 0))
    evidence['ed_visits_90d'] = ed_90
    if ed_90 >= 3:
        score += 30
        drivers.append("HIGH_RECENT_ED_UTILIZATION")
    elif ed_90 == 2:
        score += 20
        drivers.append("REPEATED_ED_UTILIZATION")
    elif ed_90 == 1:
        score += 10
        
    # 3. Care Continuity (Outpatient Follow-up)
    outpatient = features.get('outpatient_visits_90d')
    if outpatient is not None:
        evidence['outpatient_visits_90d'] = outpatient
        if outpatient == 0:
            score += 30
            drivers.append("LOW_OUTPATIENT_UTILIZATION")
        elif outpatient == 1:
            score += 15
    else:
        evidence['outpatient_visits_90d'] = "DATA_UNAVAILABLE"
        
    # 4. Complex Utilization Context (Negative modifier for legitimate complex care)
    inpatient = features.get('inpatient_visits_90d', 0)
    evidence['inpatient_visits_90d'] = inpatient
    if inpatient >= 2:
        score -= 20
        drivers.append("HIGH_INPATIENT_ACUITY_CONTEXT")
        score = max(0, score)
        
    # Missing PCP Info
    evidence['pcp_engagement'] = "DATA_UNAVAILABLE"
    
    # Determine Opportunity Level
    if score >= 70:
        level = "HIGH"
    elif score >= 40:
        level = "MEDIUM"
    else:
        level = "LOW"
        
    return {
        "navigation_opportunity_score": score,
        "navigation_opportunity_level": level,
        "evidence": evidence,
        "drivers": drivers,
        "reason": f"Calculated prototype score {score}/100 based on server-derived historical evidence.",
        "score_version": "NAV_OPP_V1"
    }
