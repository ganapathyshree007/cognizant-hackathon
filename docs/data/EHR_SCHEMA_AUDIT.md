# READ-ONLY EHR DATA ARCHITECTURE AUDIT

## 1. Current Supabase Schema
Based on the current Supabase initialization schema:
- **profiles**: id (UUID FK to auth.users), email, ull_name, ole, created_at. RLS is enabled.
- **ppointments**: ppointment_id, patient_id, encounter_id, provider_name, provider_npi, pac_id, provider_specialty, ppointment_date, ppointment_time, status, care_manager_id, created_at. No RLS.
- **outcomes**: outcome_id, ppointment_id, patient_id, encounter_id, clinical_notes, ollow_up_required, consultation_date. No RLS.
- **patient_features**: PATIENT_ID, ENCOUNTER_ID, INDEX_TIMESTAMP, plus 44 numeric/categorical feature columns. No RLS.
- **udit_trail**: id, patient_id, encounter_id, eviewer_id, ction, eason, system_pathway, system_provider, selected_provider, created_at. No RLS.
- **Missing Tables**: There are currently NO patients or encounters tables in Supabase.

## 2. Current Synthea Schema
Based on local files in data/raw/:
- **patients.csv** (12k+ rows): Id (UUID), BIRTHDATE, DEATHDATE, SSN, DRIVERS, PASSPORT, PREFIX, FIRST, LAST, SUFFIX, MAIDEN, MARITAL, RACE, ETHNICITY, GENDER, BIRTHPLACE, ADDRESS, CITY, STATE, COUNTY, ZIP, LAT, LON, HEALTHCARE_EXPENSES, HEALTHCARE_COVERAGE.
  - Canonical identifier: Id
- **encounters.csv** (50k+ rows): Id (UUID), START, STOP, PATIENT (FK), ORGANIZATION, PROVIDER, PAYER, ENCOUNTERCLASS, CODE, DESCRIPTION, BASE_ENCOUNTER_COST, TOTAL_CLAIM_COST, PAYER_COVERAGE, REASONCODE, REASONDESCRIPTION.
  - Canonical identifier: Id
  - Patient relationship: PATIENT
  - Provider relationship: PROVIDER

## 3. Schema Comparison
- **Missing from Supabase**: The foundational patients and encounters tables are absent.
- **Overlap/Redundancy**: patient_features contains denormalized demographic fields (ge_at_index, gender, ace, ethnicity, marital_status) which overlap with patients.csv.
- **Conflicts**: Synthea uses Id for the primary key. The application expects PATIENT_ID and ENCOUNTER_ID.

## 4. Existing Relationships
- encounters.PATIENT -> patients.Id (Synthea)
- ppointments.patient_id -> (No foreign key in Supabase)
- outcomes.appointment_id -> ppointments.appointment_id (Supabase)

## 5. Application Data-Flow Tracing
- **Patient Search (/api/patients/search)**: Currently searches PATIENT_ID inside the patient_features table. It does not look up a real patients table.
- **Patient Profile**: Reads ge_at_index and gender from patient_features.
- **ML Scoring**: Queries patient_features by PATIENT_ID and passes the resulting row directly to the Scikit-Learn CalibratedClassifierCV model.
- **Appointments / Outcomes**: Written directly to workflow tables.
- **Conclusion**: The frontend relies entirely on the pre-computed patient_features table to simulate patient existence. 

## 6. Required EHR Tables
- **REQUIRED NOW**: patients, encounters. (Needed to act as the true source of truth for patient identity and demographics, rather than relying on the ML feature table).
- **NOT NEEDED (Runtime)**: conditions, medications, observations, procedures, careplans, llergies. (These are heavily utilized during offline feature engineering, but are not currently displayed in the UI or queried dynamically at runtime).

## 7. Optional Tables
- **OPTIONAL/FUTURE**: conditions, medications. (Could be introduced later for explainability UI, RAG context, or care manager deep-dives).

## 8. Patient ID Strategy
- **Strategy**: Use the Synthea Id (UUID) as the canonical patient_id everywhere. 
- The application already uses this UUID in patient_features.PATIENT_ID. We do not need a new generated UUID.

## 9. Encounter ID Strategy
- **Strategy**: Use the Synthea Id (UUID) as the canonical encounter_id.

## 10. Provider ID Strategy
- **Strategy**: Use the NPI (National Provider Identifier) or pac_id from the provider_index.db as the canonical provider identifier. Currently, some tables just use provider_name, which is brittle.

## 11. patient_features Lineage
- **Source**: Derived offline from Synthea CSVs.
- **Status**: Do NOT modify. The Scikit-Learn model expects exactly 44 features in a precise order. Normalizing demographics out of this table would break the model's expected input signature. This table must be maintained as a read-only artifact table.

## 12. Proposed Final Architecture
**Raw Data Layer (Read-Only Source of Truth)**
- patients (from Synthea)
- encounters (from Synthea)

**ML Feature Layer (Read-Only Model Input)**
- patient_features (Migrated exactly as-is to preserve model distribution)

**Application Workflow Layer (Transactional)**
- ppointments (FK to patients, encounters)
- outcomes (FK to appointments)
- profiles (Auth users)
- udit_trail

## 13. Risks
- Attempting to dynamically calculate ML features at runtime from conditions and medications tables instead of using the pre-computed patient_features table will likely introduce data drift or break the model input shape.
- Modifying patient_features columns will break the CalibratedClassifierCV model.

## 14. Migration Plan
1. Create patients and encounters schemas in Supabase.
2. Import limited, required columns from patients.csv and encounters.csv to Supabase.
3. Migrate patient_features.db to Supabase patient_features table intact.
4. Migrate ppointments.db to Supabase ppointments table intact.
5. Refactor the backend API to pull demographics and search results from the patients table, and restrict patient_features strictly for ML inference.

## 15. Validation Plan
- Verify patient search returns records from the new patients table.
- Run baseline model scoring and assert that the predicted probability for a given PATIENT_ID matches the baseline test exactly to 10 decimal places.
