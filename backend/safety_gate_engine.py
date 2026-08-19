import json

class SafetyGateEngine:
    def __init__(self):
        self.rules_matrix = {
            "T02": {"Severity": "RED", "Action": "Emergency Evaluation", "Reason": "Severe hypothermia"},
            "T01": {"Severity": "YELLOW", "Action": "Urgent Medical Review", "Reason": "Hypothermia concern"},
            "T04": {"Severity": "YELLOW", "Action": "Urgent Medical Review", "Reason": "Fever"},
            "T05": {"Severity": "YELLOW", "Action": "Urgent Medical Review", "Reason": "Significant fever"},
            "T06": {"Severity": "RED", "Action": "Emergency Evaluation", "Reason": "Severe hyperthermia"},
            "S03": {"Severity": "RED", "Action": "Emergency Evaluation", "Reason": "Severe hypoxia"},
            "S02": {"Severity": "YELLOW", "Action": "Urgent Medical Review", "Reason": "Low oxygen saturation"},
            "HR07": {"Severity": "RED", "Action": "Emergency Evaluation", "Reason": "Severe bradycardia"},
            "HR06": {"Severity": "YELLOW", "Action": "Urgent Medical Review", "Reason": "Significant bradycardia"},
            "HR02": {"Severity": "YELLOW", "Action": "Urgent Medical Review", "Reason": "Elevated heart rate"},
            "HR03": {"Severity": "YELLOW", "Action": "Urgent Medical Review", "Reason": "Significant tachycardia"},
            "HR04": {"Severity": "RED", "Action": "Emergency Evaluation", "Reason": "Severe tachycardia"},
            "BP03": {"Severity": "RED", "Action": "Emergency Evaluation", "Reason": "Severe hypotension"},
            "BP02": {"Severity": "YELLOW", "Action": "Urgent Medical Review", "Reason": "Low blood pressure"},
            "BP04": {"Severity": "YELLOW", "Action": "Urgent Medical Review", "Reason": "Markedly elevated BP"},
            "BP05": {"Severity": "RED", "Action": "Emergency Evaluation", "Reason": "Severe hypertension"},
            "RR05": {"Severity": "RED", "Action": "Emergency Evaluation", "Reason": "Severe respiratory depression"},
            "RR04": {"Severity": "YELLOW", "Action": "Urgent Medical Review", "Reason": "Low respiratory rate"},
            "RR02": {"Severity": "YELLOW", "Action": "Urgent Medical Review", "Reason": "Elevated respiratory rate"},
            "RR03": {"Severity": "RED", "Action": "Emergency Evaluation", "Reason": "Severe respiratory distress"},
            "AV03": {"Severity": "RED", "Action": "Emergency Evaluation", "Reason": "Altered mental status (Pain)"},
            "AV04": {"Severity": "RED", "Action": "Emergency Evaluation", "Reason": "Altered mental status (Unresponsive)"},
            "AV02": {"Severity": "YELLOW", "Action": "Urgent Medical Review", "Reason": "Altered mental status (Voice)"},
            "SYM01": {"Severity": "RED", "Action": "Emergency Evaluation", "Reason": "Potential Acute Coronary Syndrome"},
            "SYM02": {"Severity": "YELLOW", "Action": "Urgent Medical Review", "Reason": "Reported shortness of breath"},
            "SYM03": {"Severity": "RED", "Action": "Emergency Evaluation", "Reason": "Severe hemorrhage"},
            "SYM04": {"Severity": "RED", "Action": "Emergency Evaluation", "Reason": "Active seizure"},
            "SYM05": {"Severity": "RED", "Action": "Emergency Evaluation", "Reason": "Anaphylaxis risk"},
            "SYM06": {"Severity": "RED", "Action": "Emergency Evaluation", "Reason": "Acute presentation of critical condition"},
            "SYM07": {"Severity": "RED", "Action": "Emergency Evaluation", "Reason": "Medication/Allergy Contraindication"},
            "PAIN01": {"Severity": "YELLOW", "Action": "Urgent Medical Review", "Reason": "Moderate pain"},
            "PAIN02": {"Severity": "YELLOW", "Action": "Urgent Medical Review", "Reason": "Severe acute pain"},
        }

    def normalize_symptoms(self, patient_data):
        normalized = {}
        for k, v in patient_data.items():
            if isinstance(v, bool) and v is True:
                # canonical string representation
                canon = k.strip().lower()
                normalized[canon] = True
        return normalized

    def evaluate(self, patient_data):
        triggers = []
        
        # Temperature (already converted to Celsius in api.py)
        temp = patient_data.get('Temperature')
        if temp is not None:
            if temp < 32.22: triggers.append(("T02", f"Temp = {temp:.2f}°C"))
            elif temp < 35.0: triggers.append(("T01", f"Temp = {temp:.2f}°C"))
            elif temp >= 40.0: triggers.append(("T06", f"Temp = {temp:.2f}°C"))
            elif temp >= 39.0: triggers.append(("T05", f"Temp = {temp:.2f}°C"))
            elif temp >= 38.0: triggers.append(("T04", f"Temp = {temp:.2f}°C"))

        # SpO2
        spo2 = patient_data.get('SpO2')
        if spo2 is not None:
            if spo2 < 92: triggers.append(("S03", f"SpO2 = {spo2}%"))
            elif spo2 <= 93: triggers.append(("S02", f"SpO2 = {spo2}%"))

        # Heart Rate
        hr = patient_data.get('Heart Rate')
        if hr is not None:
            if hr < 40: triggers.append(("HR07", f"HR = {hr} bpm"))
            elif hr < 50: triggers.append(("HR06", f"HR = {hr} bpm"))
            elif hr > 130: triggers.append(("HR04", f"HR = {hr} bpm"))
            elif hr >= 121: triggers.append(("HR03", f"HR = {hr} bpm"))
            elif hr >= 101: triggers.append(("HR02", f"HR = {hr} bpm"))

        # Systolic BP
        sbp = patient_data.get('Systolic BP')
        if sbp is not None:
            if sbp < 90: triggers.append(("BP03", f"Systolic BP = {sbp} mmHg"))
            elif sbp <= 99: triggers.append(("BP02", f"Systolic BP = {sbp} mmHg"))
            elif sbp >= 200: triggers.append(("BP05", f"Systolic BP = {sbp} mmHg"))
            elif sbp >= 181: triggers.append(("BP04", f"Systolic BP = {sbp} mmHg"))

        # Respiratory Rate
        rr = patient_data.get('Respiratory Rate')
        if rr is not None:
            if rr <= 8: triggers.append(("RR05", f"RR = {rr} bpm"))
            elif rr <= 11: triggers.append(("RR04", f"RR = {rr} bpm"))
            elif rr >= 30: triggers.append(("RR03", f"RR = {rr} bpm"))
            elif rr >= 21: triggers.append(("RR02", f"RR = {rr} bpm"))

        # AVPU
        avpu = patient_data.get('AVPU')
        if avpu is not None:
            av = str(avpu).strip().upper()
            if av in ['V', 'VOICE']: triggers.append(("AV02", f"AVPU = {av}"))
            elif av in ['P', 'PAIN']: triggers.append(("AV03", f"AVPU = {av}"))
            elif av in ['U', 'UNRESPONSIVE']: triggers.append(("AV04", f"AVPU = {av}"))

        # Pain
        pain = patient_data.get('Pain')
        if pain is not None:
            if pain >= 7: triggers.append(("PAIN02", f"Pain = {pain}/10"))
            elif pain >= 4: triggers.append(("PAIN01", f"Pain = {pain}/10"))

        # Symptoms
        syms = self.normalize_symptoms(patient_data)
        if 'chest pain' in syms: triggers.append(("SYM01", "UI Flag: Chest pain"))
        if 'shortness of breath' in syms: triggers.append(("SYM02", "UI Flag: Shortness of breath"))
        if 'bleeding' in syms: triggers.append(("SYM03", "UI Flag: Bleeding"))
        if 'convulsions' in syms: triggers.append(("SYM04", "UI Flag: Convulsions"))
        if 'allergic reaction' in syms: triggers.append(("SYM05", "UI Flag: Allergic Reaction"))
        if 'active high-risk condition' in syms: triggers.append(("SYM06", "UI Flag: Active high-risk condition"))
        if 'safety conflict' in syms: triggers.append(("SYM07", "Conflict: Contraindication detected"))
        
        return self._format_report(triggers, patient_data, syms)

    def _format_report(self, triggers, patient_data, syms):
        temp = patient_data.get('Temperature')
        
        # Symptoms are considered provided if 'No current symptoms' is passed OR there's a 'HasSymptoms' flag
        has_symptoms_flag = patient_data.get('No current symptoms') is True or patient_data.get('HasSymptoms') is True or len(syms) > 0
        
        missing_required = []
        if temp in (None, ''): missing_required.append('Temperature')
        if not has_symptoms_flag: missing_required.append('Current Symptoms')

        if not triggers:
            if missing_required:
                return {
                    "Status": "PENDING",
                    "Triggered Rule": "None",
                    "Reason": "Current clinical assessment incomplete",
                    "Supporting data": f"Missing required fields: {', '.join(missing_required)}",
                    "Recommended action": "Complete Care Assessment",
                    "Final decision": "System requires clinical data"
                }
            return {
                "Status": "GREEN",
                "Triggered Rule": "None",
                "Reason": "No detected safety red flag",
                "Supporting data": "Required parameters within normal limits",
                "Recommended action": "Proceed with automated care pathway",
                "Final decision": "System proceeds autonomously"
            }
            
        severity_order = {"RED": 2, "YELLOW": 1, "GREEN": 0}
        max_severity = "GREEN"
        highest_trigger = triggers[0]
        
        for rule_id, data in triggers:
            sev = self.rules_matrix[rule_id]["Severity"]
            if severity_order[sev] > severity_order[max_severity]:
                max_severity = sev
                highest_trigger = (rule_id, data)
                
        primary_rule_id, primary_data = highest_trigger
        rule_meta = self.rules_matrix[primary_rule_id]
        
        return {
            "Status": max_severity,
            "Triggered Rule": primary_rule_id,
            "Reason": rule_meta["Reason"],
            "Supporting data": primary_data,
            "Recommended action": rule_meta["Action"],
            "Final decision": "Human clinician/care manager now proceed" if max_severity in ["RED", "YELLOW"] else "System proceeds autonomously"
        }

def format_output(report):
    out = f"Status: {report['Status']}\n"
    out += f"Triggered Rule: {report['Triggered Rule']}\n"
    out += f"Reason: {report['Reason']}\n\n"
    out += f"Supporting data:\n{report['Supporting data']}\n\n"
    out += f"Recommended action:\n{report['Recommended action']}\n\n"
    out += f"Final decision:\n{report['Final decision']}\n"
    return out
