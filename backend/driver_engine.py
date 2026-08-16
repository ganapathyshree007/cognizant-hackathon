"""
Step 7 Navigation Driver Engine.

This engine determines the clinical or utilization reasons (drivers)
why a member was flagged for potential care navigation.
It operates deterministically using historical structured data and
never claims an ED visit was "avoidable".
"""
from typing import Dict, Any, List

def generate_drivers(features: Dict[str, Any], opportunity_level: str) -> Dict[str, Any]:
    drivers = []
    
    # Extract features
    ed_90 = features.get('ed_visits_90d', features.get('ed_visits_365d', 0))
    recent_ed = features.get('days_since_latest_ed')
    outpatient = features.get('outpatient_visits_90d')
    inpatient = features.get('inpatient_visits_90d', 0)
    chronic = features.get('chronic_condition_burden', 0)
    
    # 1. HIGH_ED_FREQUENCY
    if ed_90 >= 3:
        drivers.append({
            "driver_id": "HIGH_ED_FREQUENCY",
            "driver_name": "High ED utilization",
            "evidence": {"ed_visits_90d": ed_90},
            "source": "point_in_time_features",
            "strength": "HIGH"
        })
    elif ed_90 == 2:
        drivers.append({
            "driver_id": "REPEATED_ED_UTILIZATION",
            "driver_name": "Repeated ED utilization",
            "evidence": {"ed_visits_90d": ed_90},
            "source": "point_in_time_features",
            "strength": "MEDIUM"
        })
        
    # 2. RECENT_ED_UTILIZATION
    if recent_ed is not None and recent_ed <= 14:
        drivers.append({
            "driver_id": "RECENT_ED_UTILIZATION",
            "driver_name": "Recent ED utilization",
            "evidence": {"days_since_latest_ed": recent_ed},
            "source": "point_in_time_features",
            "strength": "HIGH" if recent_ed <= 7 else "MEDIUM"
        })
        
    # 3. LOW_OUTPATIENT_ENGAGEMENT
    if outpatient is not None and outpatient == 0:
        drivers.append({
            "driver_id": "LOW_OUTPATIENT_ENGAGEMENT",
            "driver_name": "Low outpatient engagement",
            "evidence": {"outpatient_visits_90d": outpatient},
            "source": "point_in_time_features",
            "strength": "HIGH"
        })

    # 4. HIGH_INPATIENT_UTILIZATION (Contextual Complexity)
    if inpatient >= 2:
        drivers.append({
            "driver_id": "HIGH_INPATIENT_UTILIZATION",
            "driver_name": "High inpatient utilization context",
            "evidence": {"inpatient_visits_90d": inpatient},
            "source": "point_in_time_features",
            "strength": "HIGH"
        })
        
    # 5. CARE_COORDINATION_GAP
    if chronic >= 3:
        drivers.append({
            "driver_id": "CARE_COORDINATION_GAP",
            "driver_name": "Care coordination gap",
            "evidence": {"chronic_condition_burden": chronic},
            "source": "point_in_time_features",
            "strength": "HIGH"
        })
        
    # Categorize status
    if len(drivers) >= 2:
        status = "SUPPORTED_EVIDENCE"
    elif len(drivers) == 1:
        status = "LIMITED_EVIDENCE"
    else:
        status = "INSUFFICIENT_EVIDENCE"
        drivers.append({
            "driver_id": "INSUFFICIENT_EVIDENCE",
            "driver_name": "Insufficient historical evidence",
            "evidence": {},
            "source": "system",
            "strength": "LOW"
        })
        
    return {
        "driver_status": status,
        "drivers": drivers,
        "summary": f"Identified {len([d for d in drivers if d['driver_id'] != 'INSUFFICIENT_EVIDENCE'])} supporting drivers for navigation opportunity.",
        "avoidability_claim": False
    }
