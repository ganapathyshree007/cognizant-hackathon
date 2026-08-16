# UC07 Synthea Current Clinical Context Feasibility Analysis

## 1. SYNTHEA DATASET INVENTORY

The following inventory is based on the actual Synthea dataset extracted from the repository (`d:/cognizant-hackathon-main/synthea_data`).

| File | Rows | Columns | Patient ID | Encounter ID | Date Columns | UC07 Relevance |
|---|---:|---:|---|---|---|---|
| `patients.csv` | 11,814 | 26 | `Id` | None | `BIRTHDATE`, `DEATHDATE` | Patient demographic profile |
| `encounters.csv` | 84,651 | 15 | `PATIENT` | `Id` | `START`, `STOP` | Current encounter details |
| `observations.csv` | 531,144 | 9 | `PATIENT` | `ENCOUNTER` | `DATE` | Current vitals, symptoms |
| `conditions.csv` | 38,094 | 6 | `PATIENT` | `ENCOUNTER` | `START`, `STOP` | Current and historical diagnoses |
| `medications.csv` | 56,430 | 13 | `PATIENT` | `ENCOUNTER` | `START`, `STOP` | Active prescriptions |
| `procedures.csv` | 83,823 | 9 | `PATIENT` | `ENCOUNTER` | `START`, `STOP` | Recent hospital/clinical procedures |
| `careplans.csv` | 3,931 | 9 | `PATIENT` | `ENCOUNTER` | `START`, `STOP` | Existing care management plans |
| `allergies.csv` | 794 | 15 | `PATIENT` | `ENCOUNTER` | `START`, `STOP` | Adverse reaction safety checks |
| `providers.csv` | 5,056 | 12 | None | None | None | Provider matching/recommendation |
| `organizations.csv`| 1,127 | 11 | None | None | None | Facility matching/recommendation |
| `claims.csv` | 117,889 | 31 | `PATIENTID` | `APPOINTMENTID` | `SERVICEDATE` | Not relevant (handled by CMS) |

---

## 2. CURRENT PATIENT CONTEXT

The following fields represent a patient's CURRENT clinical situation at the time they contact the system:

| Context | Source File | Source Column | Example Value | Current/Historical | UC07 Use |
|---|---|---|---|---|---|
| Chief Complaint / Encounter Type | `encounters.csv` | `ENCOUNTERCLASS` | "wellness", "emergency" | Current | Safety Gate / Navigation |
| Heart Rate | `observations.csv` | `VALUE` (where CODE="8867-4") | 78.0 | Current | Safety Gate |
| Oxygen Saturation | `observations.csv` | `VALUE` (where CODE="2708-6") | 98.0 | Current | Safety Gate |
| Blood Pressure | `observations.csv` | `VALUE` (where CODE="85354-9") | 120.0 | Current | Safety Gate |
| Respiratory Rate | `observations.csv` | `VALUE` (where CODE="9279-1") | 16.0 | Current | Safety Gate |
| Active Conditions | `conditions.csv` | `DESCRIPTION` | "Acute bronchitis" | Both (if STOP is empty) | Driver Analysis |
| Current Medications | `medications.csv` | `DESCRIPTION` | "cetirizine hydrochloride 5 MG" | Both (if STOP is empty) | Driver Analysis |
| Known Allergies | `allergies.csv` | `DESCRIPTION` | "Latex (substance)" | Historical/Current | Provider Navigation |

---

## 3. CURRENT VS HISTORICAL

To accurately separate CURRENT context from HISTORICAL data, the system must enforce strict date boundaries:

- **CURRENT**: Observations (`DATE`), Encounters (`START`), or Procedures (`START`) where the date is exactly equal to the system contact date (e.g., `observation.DATE >= CURRENT_TIMESTAMP - 1 day`).
- **HISTORICAL**: Any record where the date is entirely in the past (e.g., `encounter.STOP < CURRENT_TIMESTAMP`).
- **BOTH (ACTIVE)**: Long-term clinical state such as `conditions.csv`, `careplans.csv`, and `medications.csv`. These are current *if and only if* `START <= CURRENT_TIMESTAMP` and `STOP` is null or `STOP > CURRENT_TIMESTAMP`.

*Note: Do not simply take the "latest" record in the database, as the patient's last recorded encounter may be months old and not reflective of their current acute state.*

---

## 4. CAREGIVER UI INPUT

Based on the mentor's feedback, the caregiver (or triage nurse) should act as the real-time data entry point for the acute context, overriding or supplementing the EHR.

| UI Field | Source | Required/Optional | Used By | Stored in DB? |
|---|---|---|---|---|
| Patient ID | Manual / Scanner | Required | CMS Model Linkage | Yes (Encounter Table) |
| Current Reason for Visit | Caregiver Input | Required | Safety Gate | Yes (Encounter Table) |
| Current Oxygen Saturation | Caregiver Input | Required | Safety Gate | Yes (Observation Table) |
| Current Heart Rate / BP | Caregiver Input | Optional | Safety Gate | Yes (Observation Table) |
| Current Pain Level | Caregiver Input | Optional | Safety Gate | Yes (Observation Table) |
| Self-Reported Symptoms | Caregiver Input | Required | Safety Gate | Yes (Observation Table) |

---

## 5. EHR-LIKE DATA

The Synthea datasets provide the underlying EHR backbone that contextualizes the Caregiver's input.

| EHR Data | Synthea File | Column(s) | Example | Used For |
|---|---|---|---|---|
| Active Chronic Conditions | `conditions.csv` | `DESCRIPTION`, `START` | "Asthma" | Driver Analysis |
| Active Prescriptions | `medications.csv` | `DESCRIPTION`, `DISPENSES` | "Albuterol Inhaler" | Driver Analysis |
| Active Care Plans | `careplans.csv` | `DESCRIPTION` | "Self-care interventions" | Navigation (Follow-up) |
| Known Allergies | `allergies.csv` | `DESCRIPTION`, `SEVERITY1` | "Penicillin (SEVERE)" | Navigation constraints |
| Demographics | `patients.csv` | `BIRTHDATE`, `GENDER` | "1955-05-12" | CMS Model Linkage |

---

## 6. SAFETY GATE

The Safety Gate is deterministic and MUST run before the XGBoost model. It relies primarily on the Current Patient Context (Caregiver UI) combined with critical EHR flags.

| Safety Input | Source | Why Relevant | Current Data Available? | Suitable for Rule Engine? |
|---|---|---|---|---|
| Oxygen Saturation | Caregiver UI (`observations.csv` format) | < 90% is an acute emergency | Yes (UI) | Yes (Strict Threshold) |
| Heart Rate | Caregiver UI (`observations.csv` format) | > 120 bpm indicates acute distress | Yes (UI) | Yes (Strict Threshold) |
| Encounter Class | Caregiver UI (`encounters.csv` format) | "Emergency" vs "Wellness" intent | Yes (UI) | Yes (Categorical Rule) |
| Severe Allergy Reaction | `allergies.csv` | Anaphylaxis risk requiring ER | Yes (EHR) | Yes (Categorical Rule) |

*Fields that should NOT be used for Safety Gate*: Historical claims, chronic care plans, or base cost variables. The Safety Gate is purely for acute physiological triage.

---

## 7. DRIVER / CONTEXT ANALYSIS

The system can use the EHR layer to identify the "driver" behind the current utilization pattern, providing contextual signals to the Care Manager.

| Driver Category | Available Data | Source | Historical/Current | Possible Use |
|---|---|---|---|---|
| Clinical Condition | Active diagnosis codes | `conditions.csv` | Active (No STOP date) | Potential contributing factor |
| Medication-related | Number of active prescriptions | `medications.csv` | Active | Polypharmacy risk signal |
| Access/Care Management | Existing care plans | `careplans.csv` | Active | Is the patient ignoring a plan? |
| Social/Contextual | Address, ZIP | `patients.csv` | Current | Distance to care facilities |

---

## 8. NAVIGATION

If the Safety Gate determines the patient does *not* need the ED, the system recommends an alternative pathway.

| Input | Navigation Relevance | Example | Safety Dependency |
|---|---|---|---|
| Existing Care Plan | Recommends Care Manager Follow-up | "Self-care interventions" | Must pass Safety Gate |
| Missing PCP | Recommends Primary Care Establishment | No `PROVIDER` in recent history | Must pass Safety Gate |
| Mild Symptoms | Recommends Telehealth | "Rash", normal vitals | Must pass Safety Gate |
| Local Providers | Recommends Urgent Care Facility | `organizations.csv` spatial match | Must pass Safety Gate |

---

## 9. XGBOOST BOUNDARY

To prevent temporal leakage and maintain model integrity, the system must strictly isolate the XGBoost features from the current acute context.

| Synthea Field | Could Enter XGBoost? | Reason |
|---|---|---|
| Caregiver Vitals (O2, HR) | **NO** (CURRENT CONTEXT ONLY) | Temporal Leakage. Vitals are an outcome of the current acute event, not a prior predictor. |
| Current Encounter Class | **NO** (CURRENT CONTEXT ONLY) | Target Leakage. Knowing they are at the ER predicts the ER. |
| Historical Conditions | **YES** (SAFE FOR HISTORICAL MODEL) | Already handled by CMS diagnosis codes. |
| Historical Medications | **YES** (SAFE FOR HISTORICAL MODEL) | Point-in-time historical data. |

---

## 10. CMS + SYNTHEA ARCHITECTURE

The dual-architecture approach is technically appropriate and mathematically sound:

1. **CMS (Historical)**: Feeds the XGBoost model to generate a baseline `Repeat-ED Risk Score`.
2. **Synthea/UI (Current)**: Feeds the deterministic `Safety Gate` and `Context Analysis`.

These streams remain separate until the **Care Manager UI**, where the Risk Score and the Safety Gate Result are combined to generate a final, human-in-the-loop navigation recommendation. Joining the datasets directly is unnecessary and would risk catastrophic data leakage.

---

## 11. DATABASE REQUIREMENT

The underlying application database needs to capture the state of the workflow:

| DB Entity | Important Fields | Source | Purpose |
|---|---|---|---|
| **A. Patient Profile** | Patient ID, Demographics | `patients.csv` (Synthea) | Identity resolution |
| **B. Historical Summary** | Risk Score, Top 3 Drivers | XGBoost (CMS) | Baseline risk assessment |
| **C. Current Encounter** | Timestamp, Vitals, Symptoms | Caregiver UI | Acute context |
| **D. Safety Gate** | Status (PASS/FAIL/DIVERT) | Rule Engine | Triage determination |
| **E. Recommended Pathway** | Pathway (Urgent Care, Telehealth) | Navigation Engine | Care recommendation |
| **F. Provider Matching** | Provider ID, Facility Address | `organizations.csv` | Actionable routing |
| **G. Care Manager Decision**| Final Disposition, Notes | Care Manager UI | Human override / Audit log |

---

## 12. FINAL DATA FLOW

```
Caregiver UI (Real-time Vitals & Symptoms)
      ↓
Current Patient Context ──────→ EHR (Synthea Active Conditions/Meds)
      ↓                                    │
Application Database                       │
      ↓                                    │
Safety Gate ←──────────────────────────────┘
      ↓ (If PASS)
      │                 ┌───────────────┐
      │                 │ CMS History   │
      │                 ↓               │
      │         Historical Features     │
      │                 ↓               │
      │         XGBoost Model           │
      │                 ↓               │
      │         Repeat-ED Risk ─────────┘
      ↓                 ↓
Care Pathway Decision ←─┘
      ↓
Cognizant Provider Dataset (organizations.csv / providers.csv)
      ↓
Provider Matching
      ↓
Care Manager Review (Final UI)
```

---

## 13. FINAL RECOMMENDATION

1. **What Synthea data should be used?** `conditions.csv`, `medications.csv`, `allergies.csv`, `careplans.csv` (filtered strictly for active records), and `organizations.csv` for provider routing.
2. **What should come from the caregiver UI?** Current vitals (O2, HR, BP), chief complaint, and immediate acute symptoms.
3. **What should come from the EHR-like layer?** Active prescriptions, known severe allergies, and active chronic conditions.
4. **What should go into the Safety Gate?** Caregiver UI vitals + EHR severe allergy flags.
5. **What should be used for Driver/Context Analysis?** EHR active conditions, polypharmacy signals, and historical CMS claims utilization (Risk Score).
6. **What should be used for Navigation?** Synthea `organizations.csv` matched geographically to the patient's ZIP code for alternative facility routing.
7. **What should NOT enter XGBoost?** Any data from the caregiver UI, current vitals, or the current encounter intent.
8. **What should be stored in the database?** The complete lifecycle (UI inputs, Safety Gate status, XGBoost Risk Score, Final Care Manager disposition).
9. **How should CMS and Synthea interact?** They should NOT join directly. CMS drives the background Risk Score; Synthea drives the foreground clinical context. They meet only at the final Care Manager decision UI.
10. **Do we need another ML model?** No. The Safety Gate must be deterministic (rules-based). Another ML model for triage would be unsafe and non-explainable.
11. **What should be implemented next?** The Care Manager Application Backend (FastAPI) and the deterministc Safety Gate Rule Engine based on this architecture.
