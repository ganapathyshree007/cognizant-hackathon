import pandas as pd

def get_pathway_decision(safety_status, historical_risk_band):
    # Enforce safety hierarchy
    if safety_status == "RED":
        pathway = "P1"
        desc = "Emergency / Immediate Clinical Evaluation"
        priority = "Critical"
        prov_match = "BLOCKED"
        reason = "Critical safety finding detected. Historical risk cannot override safety status."
    elif safety_status == "YELLOW":
        pathway = "P2"
        desc = "Urgent Clinician Review"
        priority = "Urgent"
        prov_match = "CONDITIONAL after clinician review"
        reason = "Urgent safety flag detected. Requires clinical clearance before pathway assignment."
    else: # GREEN
        prov_match = "ALLOWED"
        if historical_risk_band == "HIGH":
            pathway = "P3"
            desc = "Priority Outpatient Follow-up + Care Management"
            priority = "High"
            reason = "High historical repeat-ED risk with no acute safety flags."
        elif historical_risk_band == "MODERATE":
            pathway = "P4"
            desc = "Routine Outpatient Follow-up"
            priority = "Medium"
            reason = "Moderate historical repeat-ED risk with no acute safety flags."
        else: # LOW
            pathway = "P5"
            desc = "Preventive / Routine Care Management"
            priority = "Low"
            reason = "Low historical repeat-ED risk with no acute safety flags."
            
    explanation = f"Safety Status: {safety_status}\nHistorical Risk Band: {historical_risk_band}\nRecommendation: {desc}\nSupporting factors: {reason}\nHuman Review: REQUIRED"
            
    return {
        "Safety Status": safety_status,
        "Historical Risk Band": historical_risk_band,
        "Recommended Pathway": pathway,
        "Pathway Description": desc,
        "Priority": priority,
        "Supporting Reason": reason,
        "Required Human Review": "YES",
        "Provider Matching": prov_match,
        "Explanation": explanation
    }

def main():
    safety_levels = ["RED", "YELLOW", "GREEN"]
    risk_bands = ["LOW", "MODERATE", "HIGH"]
    
    matrix_data = []
    decision_id = 1
    
    # 1. Build Decision Matrix
    for s in safety_levels:
        for r in risk_bands:
            decision = get_pathway_decision(s, r)
            decision["Decision ID"] = f"D{decision_id:02d}"
            matrix_data.append(decision)
            decision_id += 1
            
    df = pd.DataFrame(matrix_data)
    cols = ["Decision ID", "Safety Status", "Historical Risk Band", "Recommended Pathway", "Pathway Description", "Priority", "Supporting Reason", "Required Human Review", "Provider Matching", "Explanation"]
    df = df[cols]
    df.to_csv("UC07_STEP6_CARE_PATHWAY_DECISION_MATRIX.csv", index=False)
    
    # 2. Run Test Cases
    test_results_md = ""
    for idx, row in df.iterrows():
        test_results_md += f"#### Test Case {idx+1}: {row['Safety Status']} + {row['Historical Risk Band']}\n"
        test_results_md += f"**Output Pathway**: {row['Recommended Pathway']} - {row['Pathway Description']}\n"
        test_results_md += f"**Provider Matching**: {row['Provider Matching']}\n"
        test_results_md += f"**Explanation Generated**:\n```text\n{row['Explanation']}\n```\n"
        
        # Verify conditions
        assert row['Required Human Review'] == "YES"
        if row['Safety Status'] == "RED":
            assert row['Recommended Pathway'] == "P1"
        if row['Safety Status'] == "YELLOW":
            assert row['Recommended Pathway'] not in ["P4", "P5"]
            
    # 3. Generate Markdown Report
    md = f"""# UC07 Step 6: Care Pathway Decision Matrix Design & Validation

## 1. What Step 6 Does
Step 6 serves as the determinisic decision engine that integrates the predictive output of the Step-4 risk model with the acute clinical status evaluated by the Step-5 Safety Gate. It produces a final **Care Pathway Recommendation** while strictly prioritizing immediate patient safety over historical risk.

## 2. Inputs Received
A. **historical_risk_score**: Probability [0, 1] from Step-4 LightGBM.
B. **risk_band**: Operational thresholds categorizing the score into LOW, MODERATE, or HIGH (based on Step-4 calibration).
C. **safety_status**: RED, YELLOW, or GREEN from Step 5.
D. **safety_reasons**: Step-5 Rule IDs and triggering clinical data.
E. **current_context**: Validated point-in-time Synthea features.

## 3. Interaction Between Step 4 and Step 5
Step 4 operates strictly on historical state (`event_timestamp < INDEX_TIMESTAMP`). Step 5 operates strictly on the acute triage state (`event_timestamp == INDEX_TIMESTAMP`). Step 6 acts as the junction box, taking both independent outputs to form a unified clinical recommendation.

## 4. Why RED Overrides Historical Risk
Acute medical emergencies (e.g., severe hypoxia, acute chest pain) require immediate intervention regardless of a patient's historical baseline. A patient with a theoretically "Low Risk" of a repeat ED visit over 90 days may still be actively dying at the moment of triage. Safety constraints must always override probabilistic risk models.

## 5. Risk-Band Definitions
- **LOW**: Below the optimized intervention threshold.
- **MODERATE**: Above intervention threshold, standard priority.
- **HIGH**: Top quantile of risk probability requiring priority case management.

## 6. Pathway Categories
- **P1**: Emergency / Immediate Clinical Evaluation
- **P2**: Urgent Clinician Review
- **P3**: Priority Outpatient Follow-up + Care Management
- **P4**: Routine Outpatient Follow-up
- **P5**: Preventive / Routine Care Management

## 7. Complete Decision Matrix
| Decision ID | Safety Status | Risk Band | Pathway | Description | Priority | Provider Matching |
|---|---|---|---|---|---|---|
"""
    for _, row in df.iterrows():
        md += f"| {row['Decision ID']} | {row['Safety Status']} | {row['Historical Risk Band']} | {row['Recommended Pathway']} | {row['Pathway Description']} | {row['Priority']} | {row['Provider Matching']} |\n"

    md += f"""
## 8. Human-In-The-Loop Controls
Every pathway recommendation mandates **"Human care manager / clinician review required."** The system functions purely as clinical decision support. It cannot autonomously prescribe, diagnose, or deny emergency care.

## 9. Provider-Matching Boundary
- **RED**: Provider matching is BLOCKED. (Emergency escalation bypasses standard provider matching).
- **YELLOW**: Provider matching is CONDITIONAL. (Requires explicit clinician clearance).
- **GREEN**: Provider matching is ALLOWED based on pathway selection.

## 10. Leakage / Data-Safety Rules
This matrix strictly forbids the use of any future outcome data. It relies solely on the output of the frozen Step-4 and Step-5 engines, which have already been audited for point-in-time safety.

## 11. Test Combinations Results
{test_results_md}

## 12. Unresolved Clinical/Operational Decisions
- What are the exact probability bounds for LOW/MODERATE/HIGH based on the LightGBM optimal threshold (0.094)?
- What is the specific routing protocol for P3 vs P4 in the UI?
"""

    with open('UC07_STEP6_CARE_PATHWAY_DECISION_MATRIX.md', 'w') as f:
        f.write(md)
        
    print("Successfully generated UC07_STEP6_CARE_PATHWAY_DECISION_MATRIX.csv and .md")

if __name__ == "__main__":
    main()
