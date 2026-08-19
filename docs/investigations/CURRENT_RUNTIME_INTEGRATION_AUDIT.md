# CURRENT RUNTIME INTEGRATION AUDIT

## A. Shortness-of-breath Data Flow
**Trace:**
1. Care Assessment UI → The user selects "Shortness of breath".
2. Frontend builds the request payload: `{"clinical_context": {"Shortness of breath": true, ...}}`
3. Backend `/api/evaluate` receives this payload and passes `clinical_context` to `SafetyGateEngine.evaluate()`.
4. The Safety Gate checks its rules matrix (R01 to R13).
**Failure Point:** There is no rule for "Shortness of breath". The engine finds 0 triggers.
**Why GREEN is produced:** If `triggers` is empty, `_format_report` defaults to `Status: GREEN`. `api.py` then sees `GREEN` and maps it to `P5 Preventive / Routine Care Management`.
**Minimal Fix:** Add a rule for "Shortness of breath" (e.g., YELLOW or RED depending on clinical severity) in `safety_gate_engine.py`.

## B. Provider Data Flow
**Trace:**
1. Providers page UI executes: `fetch('/api/providers?page=1&limit=10&care=All')`.
2. The request hits the Vite proxy and is routed to `localhost:8000/api/providers`.
**Failure Point:** The `api.py` backend does not have any `@app.get("/api/providers")` endpoint defined. It returns a `404 Not Found`. The frontend silently ignores non-ok responses and displays "No providers found".
**Minimal Fix:** Implement the `GET /api/providers` endpoint in `api.py` to query the `provider_index.db` and return the list of providers.

## C. Appointment Creation Flow
**Trace:**
1. "Book Appointment" UI executes `POST /api/appointments` with payload containing `patient_id, encounter_id, provider_name, provider_npi, pac_id, provider_specialty, appointment_date, appointment_time`.
2. The `api.py` endpoint `create_appointment` executes: 
   `INSERT INTO appointments (appointment_id, patient_id, pac_id, provider_specialty, appointment_date, appointment_time, status, care_manager_id) VALUES (...)`.
**Failure Point:** 
- The schema of `appointments.db` lacks a `care_manager_id` column.
- The `INSERT` statement throws an `OperationalError: table appointments has no column named care_manager_id`.
- The error is silently swallowed by an `except Exception as e: print(e)` block, and a `"status": "success"` response is returned to the frontend.
- Additionally, `provider_name` and `encounter_id` are completely omitted from the SQL INSERT string.
**Minimal Fix:** Correct the SQL INSERT statement to match the actual table columns (`appointment_id`, `patient_id`, `encounter_id`, `provider_name`, `provider_npi`, `pac_id`, `provider_specialty`, `appointment_date`, `appointment_time`, `status`, `timestamp`).

## D. Appointment Retrieval Flow
**Trace:**
1. `/follow-ups` UI executes `GET /api/appointments`.
2. The `api.py` endpoint `get_all_appointments` executes: `SELECT * FROM appointments ORDER BY created_at DESC`.
**Failure Point:**
- The `appointments.db` table schema uses `timestamp`, not `created_at`.
- The SQLite query throws an `OperationalError: no such column: created_at`.
- The `except:` block silently catches the error and returns an empty list `[]`.
**Minimal Fix:** Change `ORDER BY created_at DESC` to `ORDER BY timestamp DESC` in both `get_all_appointments` and `get_appointments`.

## E. Dashboard Appointment Flow
**Trace:**
1. Dashboard UI executes `GET /api/dashboard/stats`.
2. Backend executes `SELECT COUNT(*) FROM appointments WHERE status = 'Scheduled'`.
**Failure Point:** The query syntax is correct, but because the `POST /api/appointments` endpoint silently fails during creation, the database remains empty, so the count is always 0.
**Minimal Fix:** Fixing the Appointment Creation flow (C) will automatically fix the dashboard count.

## F. Patient ID Consistency
**Verification:**
The UUID identifiers are structurally consistent across the flow (`patients.id` == `patient_features.PATIENT_ID` == `appointments.patient_id` == `encounters.id`).
**Failure Point:** During `POST /api/appointments`, the backend receives the `encounter_id` from the frontend, but completely drops it and fails to map it into `appointments.encounter_id` because it was forgotten in the INSERT statement.
**Minimal Fix:** Include `encounter_id` in the `INSERT INTO` statement as noted in (C).

## Summary of Files & Databases Involved
- **Frontend Code:** `care-assessment.tsx`, `providers.tsx`, `follow-ups.tsx`
- **Backend Code:** `api.py`, `safety_gate_engine.py`
- **Databases:** `data/appointments.db`, `data/provider_index.db`
