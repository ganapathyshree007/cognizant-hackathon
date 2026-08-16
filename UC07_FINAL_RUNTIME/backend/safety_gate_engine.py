import json

class SafetyGateEngine:
    def __init__(self):
        # We define the rules mapping
        self.rules_matrix = {
            "R01": {"Input": "SpO2", "Severity": "RED", "Action": "Emergency Escalation", "Reason": "Severe hypoxia"},
            "R02": {"Input": "Heart Rate", "Severity": "YELLOW", "Action": "Urgent Medical Review", "Reason": "Abnormal heart rate"},
            "R03": {"Input": "Respiratory Rate", "Severity": "RED", "Action": "Emergency Escalation", "Reason": "Abnormal respiratory finding"},
            "R04": {"Input": "Systolic BP", "Severity": "RED", "Action": "Emergency Escalation", "Reason": "Hypotension / possible shock"},
            "R05": {"Input": "Temperature", "Severity": "YELLOW", "Action": "Urgent Medical Review", "Reason": "Severe temperature abnormality"},
            "R06": {"Input": "AVPU", "Severity": "RED", "Action": "Emergency Escalation", "Reason": "Altered mental status"},
            "R07": {"Input": "Pain", "Severity": "YELLOW", "Action": "Urgent Medical Review", "Reason": "Severe acute pain"},
            "R08": {"Input": "Chest Pain", "Severity": "RED", "Action": "Emergency Escalation", "Reason": "Potential Acute Coronary Syndrome"},
            "R09": {"Input": "Bleeding", "Severity": "RED", "Action": "Emergency Escalation", "Reason": "Severe hemorrhage"},
            "R10": {"Input": "Convulsions", "Severity": "RED", "Action": "Emergency Escalation", "Reason": "Active seizure"},
            "R11": {"Input": "Allergic Reaction", "Severity": "RED", "Action": "Emergency Escalation", "Reason": "Anaphylaxis risk"},
            "R12": {"Input": "Active High-Risk Condition", "Severity": "RED", "Action": "Emergency Escalation", "Reason": "Acute presentation of critical condition"},
            "R13": {"Input": "Safety Conflict", "Severity": "RED", "Action": "Emergency Escalation", "Reason": "Medication/Allergy Contraindication"}
        }

    def evaluate(self, patient_data):
        triggers = []
        
        # R01: SpO2
        spo2 = patient_data.get('SpO2')
        if spo2 is not None and spo2 < 92:
            triggers.append(("R01", f"SpO2 = {spo2}%"))
            
        # R02: HR
        hr = patient_data.get('Heart Rate')
        if hr is not None and (hr < 60 or hr > 130):
            triggers.append(("R02", f"HR = {hr} bpm"))
            
        # R03: RR
        rr = patient_data.get('Respiratory Rate')
        if rr is not None and (rr < 10 or rr > 30):
            triggers.append(("R03", f"RR = {rr} breaths/min"))
            
        # R04: SBP
        sbp = patient_data.get('Systolic BP')
        if sbp is not None and sbp < 90:
            triggers.append(("R04", f"Systolic BP = {sbp} mmHg"))
            
        # R05: Temp
        temp = patient_data.get('Temperature')
        if temp is not None and (temp < 36.0 or temp > 39.0):
            triggers.append(("R05", f"Temp = {temp}°C"))
            
        # R06: AVPU
        avpu = patient_data.get('AVPU')
        if avpu in ['V', 'P', 'U']:
            triggers.append(("R06", f"AVPU = {avpu}"))
            
        # R07: Pain
        pain = patient_data.get('Pain')
        if pain is not None and pain > 7:
            triggers.append(("R07", f"Pain Score = {pain}/10"))
            
        # R08: Chest Pain
        if patient_data.get('Chest Pain') is True:
            triggers.append(("R08", "UI Flag: Sudden severe chest pain"))
            
        # R09: Heavy Bleeding
        if patient_data.get('Bleeding') is True:
            triggers.append(("R09", "UI Flag: Uncontrolled hemorrhage"))
            
        # R10: Convulsions
        if patient_data.get('Convulsions') is True:
            triggers.append(("R10", "UI Flag: Active seizure"))
            
        # R11: Allergic Reaction
        if patient_data.get('Allergic Reaction') is True:
            triggers.append(("R11", "UI Flag: Severe allergic reaction"))
            
        # R12: Conditions
        if patient_data.get('Active High-Risk Condition') is True:
            triggers.append(("R12", "Condition: Active acute presentation"))
            
        # R13: Conflict
        if patient_data.get('Safety Conflict') is True:
            triggers.append(("R13", "Conflict: Contraindication detected"))
            
        return self._format_report(triggers)

    def _format_report(self, triggers):
        if not triggers:
            return {
                "Status": "GREEN",
                "Triggered Rule": "None",
                "Reason": "No detected safety red flag",
                "Supporting data": "All evaluated parameters within normal limits",
                "Recommended action": "Proceed with automated care pathway",
                "Final decision": "System proceeds autonomously"
            }
            
        # Determine highest severity
        severity_order = {"RED": 2, "YELLOW": 1, "GREEN": 0}
        max_severity = "GREEN"
        highest_trigger = triggers[0]
        
        for rule_id, data in triggers:
            sev = self.rules_matrix[rule_id]["Severity"]
            if severity_order[sev] > severity_order[max_severity]:
                max_severity = sev
                highest_trigger = (rule_id, data)
                
        # If multiple moderate abnormalities (multiple YELLOWs) -> escalate to YELLOW/RED if desired
        # But per requirements, the highest severity rules.
        # Actually, user said: "multiple moderate abnormalities -> YELLOW". That naturally falls out if max is YELLOW.
        
        primary_rule_id, primary_data = highest_trigger
        rule_meta = self.rules_matrix[primary_rule_id]
        
        report = {
            "Status": max_severity,
            "Triggered Rule": primary_rule_id,
            "Reason": rule_meta["Reason"],
            "Supporting data": primary_data,
            "Recommended action": rule_meta["Action"],
            "Final decision": "Human clinician/care manager now proceed" if max_severity in ["RED", "YELLOW"] else "System proceeds autonomously"
        }
        
        return report

def format_output(report):
    out = f"Status: {report['Status']}\n"
    out += f"Triggered Rule: {report['Triggered Rule']}\n"
    out += f"Reason: {report['Reason']}\n\n"
    out += f"Supporting data:\n{report['Supporting data']}\n\n"
    out += f"Recommended action:\n{report['Recommended action']}\n\n"
    out += f"Final decision:\n{report['Final decision']}\n"
    return out
