import pandas as pd

def main():
    rules = [
        {
            "Rule ID": "R01",
            "Category": "Vitals",
            "Input": "Oxygen Saturation (SpO2)",
            "Threshold / Logic": "< 92%",
            "Severity": "RED",
            "Action": "Emergency Escalation",
            "Explanation": "Severe hypoxia indicating acute respiratory failure or critical compromise.",
            "Source URL": "https://www.who.int/publications/i/item/9789240040683 (WHO IITT)",
            "Clinician Confirmation": "Urgent Clinical Review Required (Safety Alert)"
        },
        {
            "Rule ID": "R02",
            "Category": "Vitals",
            "Input": "Heart Rate",
            "Threshold / Logic": "< 60 or > 130 bpm",
            "Severity": "YELLOW",
            "Action": "Urgent Medical Review",
            "Explanation": "Bradycardia or tachycardia indicating potential hemodynamic instability.",
            "Source URL": "https://www.who.int/publications/i/item/9789240040683 (WHO IITT)",
            "Clinician Confirmation": "Urgent Clinical Review Required (Safety Alert)"
        },
        {
            "Rule ID": "R03",
            "Category": "Vitals",
            "Input": "Respiratory Rate",
            "Threshold / Logic": "< 10 or > 30 breaths/min",
            "Severity": "RED",
            "Action": "Emergency Escalation",
            "Explanation": "Severe bradypnea or tachypnea; high risk of respiratory arrest or distress.",
            "Source URL": "https://www.who.int/publications/i/item/9789240040683 (WHO IITT)",
            "Clinician Confirmation": "Urgent Clinical Review Required (Safety Alert)"
        },
        {
            "Rule ID": "R04",
            "Category": "Vitals",
            "Input": "Systolic Blood Pressure",
            "Threshold / Logic": "< 90 mmHg",
            "Severity": "RED",
            "Action": "Emergency Escalation",
            "Explanation": "Hypotension indicating possible shock or severe hypoperfusion.",
            "Source URL": "https://www.who.int/publications/i/item/9789240040683 (WHO IITT)",
            "Clinician Confirmation": "Urgent Clinical Review Required (Safety Alert)"
        },
        {
            "Rule ID": "R05",
            "Category": "Vitals",
            "Input": "Temperature",
            "Threshold / Logic": "< 36.0°C or > 39.0°C",
            "Severity": "YELLOW",
            "Action": "Urgent Medical Review",
            "Explanation": "Severe hypothermia or hyperthermia.",
            "Source URL": "https://www.who.int/publications/i/item/9789240040683 (WHO IITT)",
            "Clinician Confirmation": "Urgent Clinical Review Required (Safety Alert)"
        },
        {
            "Rule ID": "R06",
            "Category": "Caregiver / UI",
            "Input": "Altered / Unresponsive State",
            "Threshold / Logic": "AVPU scale: V (Voice), P (Pain), or U (Unresponsive)",
            "Severity": "RED",
            "Action": "Emergency Escalation",
            "Explanation": "Altered mental status or unconsciousness; indicates severe neurological or systemic failure.",
            "Source URL": "https://www.who.int/publications/i/item/9789240040683 (WHO IITT)",
            "Clinician Confirmation": "Yes (Requires subjective UI assessment)"
        },
        {
            "Rule ID": "R07",
            "Category": "Caregiver / UI",
            "Input": "Severe Pain",
            "Threshold / Logic": "Pain Score > 7/10 or Sudden intractable pain",
            "Severity": "YELLOW",
            "Action": "Urgent Medical Review",
            "Explanation": "Severe acute pain requires rapid evaluation and analgesia.",
            "Source URL": "https://www.who.int/publications/i/item/9789240040683 (WHO IITT)",
            "Clinician Confirmation": "Yes (Subjective assessment)"
        },
        {
            "Rule ID": "R08",
            "Category": "Caregiver / UI",
            "Input": "Chest Pain (Acute)",
            "Threshold / Logic": "UI Flag: Sudden severe chest pain, radiation to jaw/arm, or chest tightness",
            "Severity": "RED",
            "Action": "Emergency Escalation",
            "Explanation": "Potential Acute Coronary Syndrome (ACS) or myocardial infarction.",
            "Source URL": "https://www.ahajournals.org/doi/10.1161/CIR.0000000000001029 (AHA Chest Pain)",
            "Clinician Confirmation": "Yes (UI Input Required)"
        },
        {
            "Rule ID": "R09",
            "Category": "Caregiver / UI",
            "Input": "Heavy Bleeding",
            "Threshold / Logic": "UI Flag: Uncontrolled or severe hemorrhage",
            "Severity": "RED",
            "Action": "Emergency Escalation",
            "Explanation": "Exsanguination risk requiring immediate trauma/surgical intervention.",
            "Source URL": "https://www.who.int/publications/i/item/9789240040683 (WHO IITT)",
            "Clinician Confirmation": "Yes (UI Input Required)"
        },
        {
            "Rule ID": "R10",
            "Category": "Caregiver / UI",
            "Input": "Active Convulsions",
            "Threshold / Logic": "UI Flag: Actively seizing at time of triage",
            "Severity": "RED",
            "Action": "Emergency Escalation",
            "Explanation": "Status epilepticus or acute seizure requiring immediate stabilization.",
            "Source URL": "https://www.who.int/publications/i/item/9789240040683 (WHO IITT)",
            "Clinician Confirmation": "Yes (UI Input Required)"
        },
        {
            "Rule ID": "R11",
            "Category": "Caregiver / UI",
            "Input": "Severe Allergic Reaction",
            "Threshold / Logic": "UI Flag: Sudden swelling of lips/throat, severe rash, or stridor",
            "Severity": "RED",
            "Action": "Emergency Escalation",
            "Explanation": "Anaphylaxis risk requiring immediate epinephrine.",
            "Source URL": "https://www.who.int/publications/i/item/9789240040683 (WHO IITT)",
            "Clinician Confirmation": "Yes (UI Input Required)"
        },
        {
            "Rule ID": "R12",
            "Category": "Synthea Conditions",
            "Input": "Active High-Risk Conditions",
            "Threshold / Logic": "Active 'Sepsis', 'Myocardial Infarction', 'Stroke', 'Pulmonary Embolism' AND matching acute presentation in Encounter Reason",
            "Severity": "RED",
            "Action": "Emergency Escalation",
            "Explanation": "Requires both the active condition and an acute current presentation flag to prevent false escalation from carried-forward chronic statuses.",
            "Source URL": "Standard Emergency Medicine Protocols",
            "Clinician Confirmation": "System lookup + UI/Encounter matching"
        },
        {
            "Rule ID": "R13",
            "Category": "Synthea Conflicts",
            "Input": "Medication / Allergy Safety Conflict",
            "Threshold / Logic": "Proposed pathway medication intersects with Active Allergies",
            "Severity": "RED",
            "Action": "Emergency Escalation",
            "Explanation": "Direct contraindication preventing safe automated pathway assignment.",
            "Source URL": "Standard Pharmacy Protocols",
            "Clinician Confirmation": "System lookup"
        }
    ]

    df = pd.DataFrame(rules)
    df.to_csv("UC07_STEP5_CLINICAL_RULES_MATRIX.csv", index=False)

    md_content = "# UC07 Step 5: Clinical Rules Matrix (Safety Gate)\n\n"
    md_content += "This matrix defines the deterministic, auditable rules for the Step 5 Safety Gate. It aligns with WHO acuity standards by classifying triggers into **RED** (Emergency escalation), **YELLOW** (Urgent clinician review), and **GREEN** (No detected safety red flag). **All rules must evaluate to GREEN before a non-emergency pathway is authorized.**\n\n"
    md_content += "## Authoritative Sources\n- [WHO Interagency Integrated Triage Tool (IITT)](https://www.who.int/publications/i/item/9789240040683)\n- [2021 AHA/ACC/ASE/CHEST/SAEM/SCCT/SCMR Guideline for the Evaluation and Diagnosis of Chest Pain](https://www.ahajournals.org/doi/10.1161/CIR.0000000000001029)\n\n"
    
    md_content += "## Safety Gate Rules\n\n"
    
    for _, row in df.iterrows():
        md_content += f"### {row['Rule ID']}: {row['Input']}\n"
        md_content += f"- **Category**: {row['Category']}\n"
        md_content += f"- **Threshold / Logic**: `{row['Threshold / Logic']}`\n"
        md_content += f"- **Severity**: **{row['Severity']}**\n"
        md_content += f"- **Action**: {row['Action']}\n"
        md_content += f"- **Explanation**: {row['Explanation']}\n"
        md_content += f"- **Source URL**: [{row['Source URL'].split(' ')[0]}]({row['Source URL'].split(' ')[0]})\n"
        md_content += f"- **Clinician Confirmation**: {row['Clinician Confirmation']}\n"
        md_content += "\n---\n\n"

    with open("UC07_STEP5_CLINICAL_RULES_MATRIX.md", "w") as f:
        f.write(md_content)
        
    print("Matrix generated successfully.")

if __name__ == "__main__":
    main()
