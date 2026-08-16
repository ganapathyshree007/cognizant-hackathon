# UC07 Step 7: Provider Matching Feasibility Audit

## 1. Available Provider Data
Synthea `providers.csv` contains 5056 unique provider records. Missingness is extremely low: Specialty missingness is 0.0%, and Location (Lat/Lon) missingness is 0.0%.

## 2. Usable Attributes
- `SPECIALITY` (e.g., GENERAL PRACTICE, CLINICAL PSYCHOLOGIST, PHYSICAL THERAPY, CLINICAL SOCIAL WORKER, CHIROPRACTIC...)
- `LAT` and `LON` (for precise distance calculations)
- `UTILIZATION` (as a historical proxy)

## 3. Missing Attributes
Synthea strictly lacks: Telehealth compatibility, Insurance/Network eligibility, "Accepting New Patients" status, and Real-Time Availability schedules.

## 4. Pathway-to-Specialty Mapping
Specialty mapping is dynamically driven by the Step-5 clinical context (e.g., an acute cardiac history routes to `Cardiology`). If standard care management is required, it maps to `General Practice` or `Internal Medicine`.

## 5. Required Eligibility Filters
- **Safety Status Constraint**: RED entirely blocks matching. YELLOW suspends matching pending manual clinician clearance.
- **Specialty Constraint**: Provider `SPECIALITY` must perfectly match the dynamically requested specialty.

## 6. Available Ranking Factors
1. **Geographic Distance**: Primary ranking factor. Computed via Haversine formula from patient to provider.
2. **Historical Utilization**: Used strictly as a tie-breaker, never interpreted as current real-time capacity.

## 7. Unusable Factors
Telehealth and Network filtering cannot be executed on Synthea data without fabricating data, which is explicitly forbidden in this architecture. Patients are never blocked due to missing preferences.

## 8. Handling of RED/YELLOW Cases
Safety immediately overrides distance matching:
- **RED**: Escalate to Emergency immediately.
- **YELLOW**: Hard stop until human override.

## 9. Enforcement of Human Review
The system yields "Recommended Options", NOT a final selection. The Care Manager evaluates the output array and clicks confirm.

## 10. Remaining Limitations
Without live API connections to scheduling databases, "distance" is mathematically the only strong signal.

## 11. Production Requirements
A production deployment requires live integration with Provider Directory APIs (e.g., FHIR endpoints) to query real-time capacity, NPI numbers, and active insurance networks.

## 12. Final Architecture
1. **Inputs**: Approved Pathway, Safety Status, Contextual Specialty, Patient Lat/Lon
2. **Hard Filter**: Safety clearances & Exact Specialty match. (Returns "No eligible provider found" if empty).
3. **Soft Rank**: Sorted by shortest Geographic Distance.
4. **Output**: List of top 3 ranked provider candidates.

---
## Internal Test Case Execution
#### Scenario: 1. RED patient
- **Status**: BLOCKED
- **Reason**: Provider matching blocked for RED safety status. Emergency escalation active.

#### Scenario: 2. YELLOW patient (No Clearance)
- **Status**: CONDITIONAL
- **Reason**: Clinician clearance required for YELLOW safety status before provider selection.

#### Scenario: 3. GREEN + P3 (Primary Care)
- **Status**: NO_MATCH
- **Reason**: No eligible provider found matching required specialty.

#### Scenario: 4. GREEN + Specialist
- **Status**: NO_MATCH
- **Reason**: No eligible provider found matching required specialty.

#### Scenario: 5. Telehealth Requested
- **Status**: NO_MATCH
- **Reason**: No eligible provider found matching required specialty.

#### Scenario: 6. No nearby provider (Mocking distant lat/lon)
- **Status**: NO_MATCH
- **Reason**: No eligible provider found matching required specialty.

#### Scenario: 7. Missing optional patient preference
- **Status**: NO_MATCH
- **Reason**: No eligible provider found matching required specialty.

#### Scenario: 8. No eligible provider (Fake Specialty)
- **Status**: NO_MATCH
- **Reason**: No eligible provider found matching required specialty.


