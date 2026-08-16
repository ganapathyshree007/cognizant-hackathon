# UC07 Step 6: Care Pathway Decision Matrix Design & Validation

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
| D01 | RED | LOW | P1 | Emergency / Immediate Clinical Evaluation | Critical | BLOCKED |
| D02 | RED | MODERATE | P1 | Emergency / Immediate Clinical Evaluation | Critical | BLOCKED |
| D03 | RED | HIGH | P1 | Emergency / Immediate Clinical Evaluation | Critical | BLOCKED |
| D04 | YELLOW | LOW | P2 | Urgent Clinician Review | Urgent | CONDITIONAL after clinician review |
| D05 | YELLOW | MODERATE | P2 | Urgent Clinician Review | Urgent | CONDITIONAL after clinician review |
| D06 | YELLOW | HIGH | P2 | Urgent Clinician Review | Urgent | CONDITIONAL after clinician review |
| D07 | GREEN | LOW | P5 | Preventive / Routine Care Management | Low | ALLOWED |
| D08 | GREEN | MODERATE | P4 | Routine Outpatient Follow-up | Medium | ALLOWED |
| D09 | GREEN | HIGH | P3 | Priority Outpatient Follow-up + Care Management | High | ALLOWED |

## 8. Human-In-The-Loop Controls
Every pathway recommendation mandates **"Human care manager / clinician review required."** The system functions purely as clinical decision support. It cannot autonomously prescribe, diagnose, or deny emergency care.

## 9. Provider-Matching Boundary
- **RED**: Provider matching is BLOCKED. (Emergency escalation bypasses standard provider matching).
- **YELLOW**: Provider matching is CONDITIONAL. (Requires explicit clinician clearance).
- **GREEN**: Provider matching is ALLOWED based on pathway selection.

## 10. Leakage / Data-Safety Rules
This matrix strictly forbids the use of any future outcome data. It relies solely on the output of the frozen Step-4 and Step-5 engines, which have already been audited for point-in-time safety.

## 11. Test Combinations Results
#### Test Case 1: RED + LOW
**Output Pathway**: P1 - Emergency / Immediate Clinical Evaluation
**Provider Matching**: BLOCKED
**Explanation Generated**:
```text
Safety Status: RED
Historical Risk Band: LOW
Recommendation: Emergency / Immediate Clinical Evaluation
Supporting factors: Critical safety finding detected. Historical risk cannot override safety status.
Human Review: REQUIRED
```
#### Test Case 2: RED + MODERATE
**Output Pathway**: P1 - Emergency / Immediate Clinical Evaluation
**Provider Matching**: BLOCKED
**Explanation Generated**:
```text
Safety Status: RED
Historical Risk Band: MODERATE
Recommendation: Emergency / Immediate Clinical Evaluation
Supporting factors: Critical safety finding detected. Historical risk cannot override safety status.
Human Review: REQUIRED
```
#### Test Case 3: RED + HIGH
**Output Pathway**: P1 - Emergency / Immediate Clinical Evaluation
**Provider Matching**: BLOCKED
**Explanation Generated**:
```text
Safety Status: RED
Historical Risk Band: HIGH
Recommendation: Emergency / Immediate Clinical Evaluation
Supporting factors: Critical safety finding detected. Historical risk cannot override safety status.
Human Review: REQUIRED
```
#### Test Case 4: YELLOW + LOW
**Output Pathway**: P2 - Urgent Clinician Review
**Provider Matching**: CONDITIONAL after clinician review
**Explanation Generated**:
```text
Safety Status: YELLOW
Historical Risk Band: LOW
Recommendation: Urgent Clinician Review
Supporting factors: Urgent safety flag detected. Requires clinical clearance before pathway assignment.
Human Review: REQUIRED
```
#### Test Case 5: YELLOW + MODERATE
**Output Pathway**: P2 - Urgent Clinician Review
**Provider Matching**: CONDITIONAL after clinician review
**Explanation Generated**:
```text
Safety Status: YELLOW
Historical Risk Band: MODERATE
Recommendation: Urgent Clinician Review
Supporting factors: Urgent safety flag detected. Requires clinical clearance before pathway assignment.
Human Review: REQUIRED
```
#### Test Case 6: YELLOW + HIGH
**Output Pathway**: P2 - Urgent Clinician Review
**Provider Matching**: CONDITIONAL after clinician review
**Explanation Generated**:
```text
Safety Status: YELLOW
Historical Risk Band: HIGH
Recommendation: Urgent Clinician Review
Supporting factors: Urgent safety flag detected. Requires clinical clearance before pathway assignment.
Human Review: REQUIRED
```
#### Test Case 7: GREEN + LOW
**Output Pathway**: P5 - Preventive / Routine Care Management
**Provider Matching**: ALLOWED
**Explanation Generated**:
```text
Safety Status: GREEN
Historical Risk Band: LOW
Recommendation: Preventive / Routine Care Management
Supporting factors: Low historical repeat-ED risk with no acute safety flags.
Human Review: REQUIRED
```
#### Test Case 8: GREEN + MODERATE
**Output Pathway**: P4 - Routine Outpatient Follow-up
**Provider Matching**: ALLOWED
**Explanation Generated**:
```text
Safety Status: GREEN
Historical Risk Band: MODERATE
Recommendation: Routine Outpatient Follow-up
Supporting factors: Moderate historical repeat-ED risk with no acute safety flags.
Human Review: REQUIRED
```
#### Test Case 9: GREEN + HIGH
**Output Pathway**: P3 - Priority Outpatient Follow-up + Care Management
**Provider Matching**: ALLOWED
**Explanation Generated**:
```text
Safety Status: GREEN
Historical Risk Band: HIGH
Recommendation: Priority Outpatient Follow-up + Care Management
Supporting factors: High historical repeat-ED risk with no acute safety flags.
Human Review: REQUIRED
```


## 12. Unresolved Clinical/Operational Decisions
- What are the exact probability bounds for LOW/MODERATE/HIGH based on the LightGBM optimal threshold (0.094)?
- What is the specific routing protocol for P3 vs P4 in the UI?
