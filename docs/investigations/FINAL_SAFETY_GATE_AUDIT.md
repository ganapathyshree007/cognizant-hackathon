# FULL SAFETY GATE RULE AUDIT (READ ONLY)

## A. CURRENT RULE COUNT
There are exactly **14** deterministic rules implemented in `safety_gate_engine.py` (`R01` through `R14`).

## B. COMPLETE RULE TABLE

| Rule ID | Input | Condition | Severity | Action | Reason | Source file | Function |
|---------|-------|-----------|----------|--------|--------|-------------|----------|
| R01 | SpO2 | `< 92` | RED | Emergency Escalation | Severe hypoxia | `safety_gate_engine.py` | `evaluate()` |
| R02 | Heart Rate | `< 60` or `> 130` | YELLOW | Urgent Medical Review | Abnormal heart rate | `safety_gate_engine.py` | `evaluate()` |
| R03 | Respiratory Rate | `< 10` or `> 30` | RED | Emergency Escalation | Abnormal respiratory finding | `safety_gate_engine.py` | `evaluate()` |
| R04 | Systolic BP | `< 90` | RED | Emergency Escalation | Hypotension / possible shock | `safety_gate_engine.py` | `evaluate()` |
| R05 | Temperature | `< 36.0` or `> 39.0` | YELLOW | Urgent Medical Review | Severe temperature abnormality | `safety_gate_engine.py` | `evaluate()` |
| R06 | AVPU | `in ['V', 'P', 'U']` | RED | Emergency Escalation | Altered mental status | `safety_gate_engine.py` | `evaluate()` |
| R07 | Pain | `> 7` | YELLOW | Urgent Medical Review | Severe acute pain | `safety_gate_engine.py` | `evaluate()` |
| R08 | Chest Pain | `is True` | RED | Emergency Escalation | Potential Acute Coronary Syndrome | `safety_gate_engine.py` | `evaluate()` |
| R09 | Bleeding | `is True` | RED | Emergency Escalation | Severe hemorrhage | `safety_gate_engine.py` | `evaluate()` |
| R10 | Convulsions | `is True` | RED | Emergency Escalation | Active seizure | `safety_gate_engine.py` | `evaluate()` |
| R11 | Allergic Reaction | `is True` | RED | Emergency Escalation | Anaphylaxis risk | `safety_gate_engine.py` | `evaluate()` |
| R12 | Active High-Risk Condition | `is True` | RED | Emergency Escalation | Acute presentation... | `safety_gate_engine.py` | `evaluate()` |
| R13 | Safety Conflict | `is True` | RED | Emergency Escalation | Medication/Allergy Contraindication | `safety_gate_engine.py` | `evaluate()` |
| R14 | Shortness of breath | `is True` | YELLOW | Urgent Medical Review | Reported shortness of breath... | `safety_gate_engine.py` | `evaluate()` |

*Note: There are no duplicated rules, and all rules exist inside the primary rules matrix.*

## C. VITAL THRESHOLD TABLE

| Vital | Normal Range / Safe | YELLOW Trigger | RED Trigger | Missing Behavior | Frontend Field | Backend Field | Reaches Gate? |
|-------|----------------------|----------------|-------------|------------------|----------------|---------------|---------------|
| Temperature | `36.0 - 39.0` (Celsius) | `< 36.0` or `> 39.0` | None | PENDING | `Temperature` | `Temperature` | Yes |
| SpO2 | `>= 92` | None | `< 92` | PENDING | `SpO2` | `SpO2` | Yes |
| Heart Rate | `60 - 130` | `< 60` or `> 130` | None | PENDING | `Heart Rate` | `Heart Rate` | Yes |
| Systolic BP | `>= 90` | None | `< 90` | PENDING | `Systolic BP` | `Systolic BP` | Yes |
| Respiratory Rate| `10 - 30` | None | `< 10` or `> 30` | PENDING | `Respiratory Rate`| `Respiratory Rate` | Yes |
| AVPU | `'A'` or not V,P,U | None | `'V', 'P', 'U'` | PENDING | `AVPU` | `AVPU` | Yes |
| Pain | `<= 7` | `> 7` | None | Ignored | `Pain` | `Pain` | Yes |

**Logical Inconsistency Found:** 
The frontend provides "normal" Temperature in Fahrenheit (e.g., `98.6`), but the backend evaluates it in Celsius (`< 36.0 or > 39.0`). Thus, `98.6` evaluates as `> 39.0` and incorrectly triggers YELLOW (R05).

## D. SYMPTOM RULE TABLE

| Symptom | Generates | Missing Behavior | Is AI Extracted? | Interacts w/ Vitals? |
|---------|-----------|------------------|------------------|----------------------|
| Cough | None | Ignored | No (Not in LLM prompt)| No |
| Fever | None | Ignored | Yes | No |
| Shortness of breath | YELLOW | Ignored | No (Not in LLM prompt)| No |
| Chest Pain | RED | Ignored | Yes | No |
| Bleeding | RED | Ignored | Yes | No |
| Convulsions | RED | Ignored | Yes | No |
| Allergic Reaction | RED | Ignored | Yes | No |

**CRITICAL DISCOVERY:**
Why does "Cough + normal vitals + AVPU Alert" produce YELLOW?
It is NOT because of Cough. "Normal vitals" in the US generally implies a temperature around 98.6°F. Because the Safety Gate checks if Temperature is `> 39.0` (Celsius), entering `98.6` automatically triggers **Rule R05 (Severe temperature abnormality - YELLOW)**. Cough is entirely ignored by the logic.

## E. SEVERITY PRECEDENCE
The actual implementation follows:
`RED > YELLOW > GREEN`
`highest_trigger = triggers[0]` is then re-evaluated by comparing it against `severity_order = {"RED": 2, "YELLOW": 1, "GREEN": 0}`.
The code accurately ensures that a RED trigger will always dominate a YELLOW trigger, and YELLOW dominates GREEN.

## F. PENDING LOGIC
The logic accurately enforces:
- No triggers + missing required vitals → `PENDING`
- YELLOW trigger + missing required vitals → `YELLOW`
- RED trigger + missing required vitals → `RED`
Because the `missing_vitals` check occurs inside `if not triggers:`, it perfectly implements the design requirement. If a severe trigger is present, it will fire even if other vitals are absent.

## G. HISTORICAL RISK VS CURRENT SAFETY
Verified: The historical risk model (`predict_proba`) correctly operates completely independently of the Safety Gate.
- HIGH historical risk + GREEN current safety → `GREEN` current safety (and P3 Pathway).
- LOW historical risk + RED current safety → `RED` current safety (and P1 Pathway).
Historical risk correctly maps to pathways (P3, P4, P5) and does not suppress or inflate the deterministically calculated Safety Gate status.

## H. CARE PATHWAY MAPPING
`compute_care_pathway()` precisely maps:
- `PENDING` → Assessment Required (Pathway: Assessment Required)
- `GREEN` → P3, P4, or P5 (depending on historical risk)
- `YELLOW` → P2 (Urgent Clinician Review)
- `RED` → P1 (Emergency / Immediate Clinical Evaluation)
This mapping is correct.

## I. PROVIDER MATCHING BEHAVIOR
**MAJOR BUG FOUND:**
In `api.py` lines 270-272:
```python
    if safety_status == 'PENDING':
        provider_result = {"Status": "BLOCKED", "Reason": "Current clinical information is required.", "Options": []}
    else:
        df_providers = get_real_providers_by_specialty(req_specialty)
```
RED and YELLOW are NOT blocked. The `else` block runs for GREEN, YELLOW, and RED. This means RED and YELLOW statuses incorrectly proceed to retrieve routine provider matches from `provider_index.db`. 

## J. APPOINTMENT SAFETY
Currently, if Provider Matching is improperly executed (as detailed in Section I), the frontend can theoretically allow a user to select a provider and click "Book" even if the patient is RED. The backend `/api/appointments` endpoint only verifies the payload and does not re-verify the `Safety Status`. 

## K. FRONTEND/BACKEND FIELD MISMATCHES
1. **Chest pain:** Frontend dropdown sends `"Chest pain"` (lowercase 'p'). Backend expects `"Chest Pain"` (Capital 'P'). Rule R08 will fail if manually selected. (The LLM extracts `"Chest Pain"`, so natural language works, but the dropdown fails).
2. **Shortness of breath:** Matches exactly between frontend dropdown and backend rule R14. However, the LLM prompt does not list it as a possible key, so it relies entirely on the manual dropdown or lucky LLM generation.
3. **Safety Conflict:** Backend R13 expects `"Safety Conflict"`, but no frontend UI element or LLM prompt exists to populate this.

## L. 14-TEST VALIDATION MATRIX

| Test | Expected | Actual | Status | Reason |
|------|----------|--------|--------|--------|
| 1. No current clinical data | PENDING | PENDING | PASS | Missing vitals with no triggers |
| 2. All required vitals normal | GREEN | YELLOW | FAIL | `98.6` triggers R05 Temp > 39.0 (Celsius mismatch) |
| 3. Normal vitals + isolated Cough | GREEN | YELLOW | FAIL | Cough is ignored, but `98.6` triggers R05 |
| 4. Shortness of breath + normal SpO2 | YELLOW | YELLOW | PASS | Triggers R14 |
| 5. Shortness of breath + SpO2 < 92% | RED | RED | PASS | R01 (RED) overrides R14 (YELLOW) |
| 6. Normal vitals + severe chest pain | RED | RED | PASS | R08 triggers RED (if extracted via LLM) |
| 7. Missing vitals + no trigger | PENDING | PENDING | PASS | `if not triggers: return PENDING` |
| 8. Missing vitals + YELLOW trigger | YELLOW | YELLOW | PASS | Skips missing_vitals check, returns YELLOW |
| 9. Missing vitals + RED trigger | RED | RED | PASS | Skips missing_vitals check, returns RED |
| 10. High historical risk + normal | GREEN | YELLOW | FAIL | Temp=98.6 triggers YELLOW (would be GREEN otherwise) |
| 11. Low historical risk + RED | RED | RED | PASS | RED overrides all historical pathways |
| 12. Multiple triggers including RED | RED | RED | PASS | Precedence matrix correctly maps max severity |
| 13. Multiple YELLOW triggers | YELLOW | YELLOW | PASS | Max severity remains YELLOW |
| 14. Normal assessment + no symptoms | GREEN | YELLOW | FAIL | Temp=98.6 triggers YELLOW |

## M. BUGS FOUND
1. **Celsius/Fahrenheit Mismatch:** The UI provides Temperature in Fahrenheit, but the backend gate assesses it in Celsius (`> 39.0`).
2. **RED/YELLOW Provider Routing Leak:** `api.py` step7 allows RED and YELLOW to execute provider matching because it only explicitly blocks `PENDING`.
3. **Casing Mismatch on Chest Pain:** Manual dropdown sends `"Chest pain"`, bypassing rule R08 which demands `"Chest Pain"`.
4. **Missing Prompt Directives:** The LLM is not instructed to extract `"Shortness of breath"`.

## N. RULES THAT ARE CORRECT
All existing rules in `safety_gate_engine.py` (R01 - R14) are structurally correct. The PENDING logic is perfect. The Severity precedence is perfect. The separation of Historical Risk from Current Safety is perfect.

## O. RULES THAT NEED CHANGES
No clinical rules in `safety_gate_engine.py` need rewriting. The logic is mathematically sound. The issues exist purely in unit conversion, casing, and routing control.

## P. MINIMAL FIX PLAN
1. In `api.py`: Convert Fahrenheit to Celsius during the float casting block.
2. In `api.py`: Block provider matching for RED (return `Options: []`). Allow YELLOW according to clinical intent.
3. In `care-assessment.tsx`: Change the dropdown value from `"Chest pain"` to `"Chest Pain"`.
4. In `api.py`: Add `"Shortness of breath" (true)` and `"Safety Conflict" (true)` to the LLM system prompt.

## Q. FILES THAT WOULD NEED MODIFICATION
- `UC07_FINAL_RUNTIME/backend/api.py`
- `UIUX_CTS/app/routes/care-assessment.tsx`

*(No modifications have been made during this audit)*
