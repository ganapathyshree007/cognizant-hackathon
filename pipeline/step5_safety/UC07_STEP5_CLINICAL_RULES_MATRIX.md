# UC07 Step 5: Clinical Rules Matrix (Safety Gate)

This matrix defines the deterministic, auditable rules for the Step 5 Safety Gate. It aligns with WHO acuity standards by classifying triggers into **RED** (Emergency escalation), **YELLOW** (Urgent clinician review), and **GREEN** (No detected safety red flag). **All rules must evaluate to GREEN before a non-emergency pathway is authorized.**

## Authoritative Sources
- [WHO Interagency Integrated Triage Tool (IITT)](https://www.who.int/publications/i/item/9789240040683)
- [2021 AHA/ACC/ASE/CHEST/SAEM/SCCT/SCMR Guideline for the Evaluation and Diagnosis of Chest Pain](https://www.ahajournals.org/doi/10.1161/CIR.0000000000001029)

## Safety Gate Rules

### R01: Oxygen Saturation (SpO2)
- **Category**: Vitals
- **Threshold / Logic**: `< 92%`
- **Severity**: **RED**
- **Action**: Emergency Escalation
- **Explanation**: Severe hypoxia indicating acute respiratory failure or critical compromise.
- **Source URL**: [https://www.who.int/publications/i/item/9789240040683](https://www.who.int/publications/i/item/9789240040683)
- **Clinician Confirmation**: Urgent Clinical Review Required (Safety Alert)

---

### R02: Heart Rate
- **Category**: Vitals
- **Threshold / Logic**: `< 60 or > 130 bpm`
- **Severity**: **YELLOW**
- **Action**: Urgent Medical Review
- **Explanation**: Bradycardia or tachycardia indicating potential hemodynamic instability.
- **Source URL**: [https://www.who.int/publications/i/item/9789240040683](https://www.who.int/publications/i/item/9789240040683)
- **Clinician Confirmation**: Urgent Clinical Review Required (Safety Alert)

---

### R03: Respiratory Rate
- **Category**: Vitals
- **Threshold / Logic**: `< 10 or > 30 breaths/min`
- **Severity**: **RED**
- **Action**: Emergency Escalation
- **Explanation**: Severe bradypnea or tachypnea; high risk of respiratory arrest or distress.
- **Source URL**: [https://www.who.int/publications/i/item/9789240040683](https://www.who.int/publications/i/item/9789240040683)
- **Clinician Confirmation**: Urgent Clinical Review Required (Safety Alert)

---

### R04: Systolic Blood Pressure
- **Category**: Vitals
- **Threshold / Logic**: `< 90 mmHg`
- **Severity**: **RED**
- **Action**: Emergency Escalation
- **Explanation**: Hypotension indicating possible shock or severe hypoperfusion.
- **Source URL**: [https://www.who.int/publications/i/item/9789240040683](https://www.who.int/publications/i/item/9789240040683)
- **Clinician Confirmation**: Urgent Clinical Review Required (Safety Alert)

---

### R05: Temperature
- **Category**: Vitals
- **Threshold / Logic**: `< 36.0°C or > 39.0°C`
- **Severity**: **YELLOW**
- **Action**: Urgent Medical Review
- **Explanation**: Severe hypothermia or hyperthermia.
- **Source URL**: [https://www.who.int/publications/i/item/9789240040683](https://www.who.int/publications/i/item/9789240040683)
- **Clinician Confirmation**: Urgent Clinical Review Required (Safety Alert)

---

### R06: Altered / Unresponsive State
- **Category**: Caregiver / UI
- **Threshold / Logic**: `AVPU scale: V (Voice), P (Pain), or U (Unresponsive)`
- **Severity**: **RED**
- **Action**: Emergency Escalation
- **Explanation**: Altered mental status or unconsciousness; indicates severe neurological or systemic failure.
- **Source URL**: [https://www.who.int/publications/i/item/9789240040683](https://www.who.int/publications/i/item/9789240040683)
- **Clinician Confirmation**: Yes (Requires subjective UI assessment)

---

### R07: Severe Pain
- **Category**: Caregiver / UI
- **Threshold / Logic**: `Pain Score > 7/10 or Sudden intractable pain`
- **Severity**: **YELLOW**
- **Action**: Urgent Medical Review
- **Explanation**: Severe acute pain requires rapid evaluation and analgesia.
- **Source URL**: [https://www.who.int/publications/i/item/9789240040683](https://www.who.int/publications/i/item/9789240040683)
- **Clinician Confirmation**: Yes (Subjective assessment)

---

### R08: Chest Pain (Acute)
- **Category**: Caregiver / UI
- **Threshold / Logic**: `UI Flag: Sudden severe chest pain, radiation to jaw/arm, or chest tightness`
- **Severity**: **RED**
- **Action**: Emergency Escalation
- **Explanation**: Potential Acute Coronary Syndrome (ACS) or myocardial infarction.
- **Source URL**: [https://www.ahajournals.org/doi/10.1161/CIR.0000000000001029](https://www.ahajournals.org/doi/10.1161/CIR.0000000000001029)
- **Clinician Confirmation**: Yes (UI Input Required)

---

### R09: Heavy Bleeding
- **Category**: Caregiver / UI
- **Threshold / Logic**: `UI Flag: Uncontrolled or severe hemorrhage`
- **Severity**: **RED**
- **Action**: Emergency Escalation
- **Explanation**: Exsanguination risk requiring immediate trauma/surgical intervention.
- **Source URL**: [https://www.who.int/publications/i/item/9789240040683](https://www.who.int/publications/i/item/9789240040683)
- **Clinician Confirmation**: Yes (UI Input Required)

---

### R10: Active Convulsions
- **Category**: Caregiver / UI
- **Threshold / Logic**: `UI Flag: Actively seizing at time of triage`
- **Severity**: **RED**
- **Action**: Emergency Escalation
- **Explanation**: Status epilepticus or acute seizure requiring immediate stabilization.
- **Source URL**: [https://www.who.int/publications/i/item/9789240040683](https://www.who.int/publications/i/item/9789240040683)
- **Clinician Confirmation**: Yes (UI Input Required)

---

### R11: Severe Allergic Reaction
- **Category**: Caregiver / UI
- **Threshold / Logic**: `UI Flag: Sudden swelling of lips/throat, severe rash, or stridor`
- **Severity**: **RED**
- **Action**: Emergency Escalation
- **Explanation**: Anaphylaxis risk requiring immediate epinephrine.
- **Source URL**: [https://www.who.int/publications/i/item/9789240040683](https://www.who.int/publications/i/item/9789240040683)
- **Clinician Confirmation**: Yes (UI Input Required)

---

### R12: Active High-Risk Conditions
- **Category**: Synthea Conditions
- **Threshold / Logic**: `Active 'Sepsis', 'Myocardial Infarction', 'Stroke', 'Pulmonary Embolism' AND matching acute presentation in Encounter Reason`
- **Severity**: **RED**
- **Action**: Emergency Escalation
- **Explanation**: Requires both the active condition and an acute current presentation flag to prevent false escalation from carried-forward chronic statuses.
- **Source URL**: [Standard](Standard)
- **Clinician Confirmation**: System lookup + UI/Encounter matching

---

### R13: Medication / Allergy Safety Conflict
- **Category**: Synthea Conflicts
- **Threshold / Logic**: `Proposed pathway medication intersects with Active Allergies`
- **Severity**: **RED**
- **Action**: Emergency Escalation
- **Explanation**: Direct contraindication preventing safe automated pathway assignment.
- **Source URL**: [Standard](Standard)
- **Clinician Confirmation**: System lookup

---

