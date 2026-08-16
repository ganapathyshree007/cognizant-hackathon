"""
Step 8 Pathway Engine

Deterministically recommends candidate care pathways based on
verified Step 7 drivers and Step 6 opportunity levels.
"""
from typing import Dict, Any, List

def recommend_pathways(
    opportunity_level: str, 
    drivers: List[Dict[str, Any]], 
    telehealth_preferred: bool = False
) -> Dict[str, Any]:
    
    driver_ids = [d['driver_id'] for d in drivers]
    
    candidates = []
    
    # Rule 1: High inpatient complexity is contextual. 
    # It does NOT automatically equal CARE_MANAGEMENT.
    has_high_inpatient = "HIGH_INPATIENT_UTILIZATION" in driver_ids
    
    # 1. PRIMARY_CARE
    if "LOW_OUTPATIENT_ENGAGEMENT" in driver_ids and opportunity_level in ("HIGH", "MEDIUM"):
        if not has_high_inpatient:
            candidates.append("PRIMARY_CARE")
            
    # 2. URGENT_CARE
    if "RECENT_ED_UTILIZATION" in driver_ids and opportunity_level in ("HIGH", "MEDIUM"):
        if not has_high_inpatient:
            candidates.append("URGENT_CARE")
            
    # 3. CARE_MANAGEMENT
    if "CARE_COORDINATION_GAP" in driver_ids and opportunity_level in ("HIGH", "MEDIUM"):
        candidates.append("CARE_MANAGEMENT")
        
    # 4. TELEHEALTH (Access context, not a default)
    if telehealth_preferred and candidates:
        # Only add Telehealth if we already have evidence supporting low-acuity navigation
        candidates.append("TELEHEALTH")
        
    # Fallback if no specific pathways are supported
    if not candidates:
        return {
            "recommended_pathway": "NO_PATHWAY_RECOMMENDATION",
            "alternative_pathways": [],
            "reason": "Available evidence does not deterministically support a specific lower-acuity care pathway. High complexity or insufficient data requires care-manager manual review.",
            "supporting_drivers": driver_ids,
            "human_review_required": True,
            "rule_version": "PATHWAY_RULES_V1"
        }
        
    # Rank candidates (Priority: CARE_MANAGEMENT > PRIMARY_CARE > TELEHEALTH > URGENT_CARE)
    priority = ["CARE_MANAGEMENT", "PRIMARY_CARE", "TELEHEALTH", "URGENT_CARE"]
    
    ranked = sorted(list(set(candidates)), key=lambda x: priority.index(x))
    
    rec = ranked[0]
    alts = ranked[1:]
    
    return {
        "recommended_pathway": rec,
        "alternative_pathways": alts,
        "reason": f"Recommendation generated based on navigation drivers: {', '.join(driver_ids)}.",
        "supporting_drivers": driver_ids,
        "human_review_required": True,
        "rule_version": "PATHWAY_RULES_V1"
    }
