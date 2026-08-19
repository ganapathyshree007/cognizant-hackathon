# CANONICAL RUNTIME AUDIT

This is a read-only audit of the current UC07 repository to definitively prove which files are actively serving the running application.

## 1. Active Frontend
The **active frontend** is located at: UIUX_CTS/
Evidence:
- Process tree confirms 
ode.exe is running UIUX_CTS\node_modules\.bin\..\vite\bin\vite.js.
- Distinctive UI strings such as "All Patients & Encounters" are uniquely found inside UIUX_CTS\app\routes\patients\index.tsx (Line 54).

## 2. Active Backend
The **active backend** is located at: UC07_FINAL_RUNTIME/backend/
Evidence:
- The backend task log and process explorer confirm that python api.py was launched with the working directory set to UC07_FINAL_RUNTIME/backend/.
- The database paths relative to __file__ map perfectly to this directory's data/ subfolder.

## 3. Exact Startup Commands
- **Frontend (Port 5173):** 
pm run dev executed inside the UIUX_CTS/ directory.
- **Backend (Port 8000):** $env:OPENROUTER_API_KEY="sk-or-..."; python api.py executed inside the UC07_FINAL_RUNTIME/backend/ directory.

## 4. localhost:5173 Source
**Source:** UIUX_CTS/
Proof: The Node process for port 5173 maps directly to the Vite binaries installed in the UIUX_CTS/node_modules/ directory.

## 5. localhost:8000 Source
**Source:** UC07_FINAL_RUNTIME/backend/
Proof: The Python process bound to port 8000 is executing the pi.py file located within UC07_FINAL_RUNTIME/backend/.

## 6. Frontend ? Backend Connection
**Connection:** The frontend connects to the backend via a Vite proxy.
Proof: UIUX_CTS/vite.config.ts explicitly proxies /api requests to http://localhost:8000. This confirms the active coupling between UIUX_CTS and UC07_FINAL_RUNTIME/backend/api.py.

## 7. Duplicate Frontend Analysis
- **UIUX_CTS/**: ACTIVE. A fully-featured React application using @tanstack/react-router, Radix UI, and Tailwind. Contains the working Patient workflow and Care Manager features.
- **UC07_FINAL_RUNTIME/frontend/**: LEGACY/UNUSED. A basic Vite template with minimal dependencies (eact-router-dom). It does not contain the distinctive application strings currently rendered in the browser.
- **rontend/**: DOES NOT EXIST.

## 8. Duplicate Backend Analysis
- **UC07_FINAL_RUNTIME/backend/**: ACTIVE. Contains the FastAPI app (pi.py), local SQLite databases, advanced matching engine, and Safety Gate logic.
- **ackend/**: LEGACY/UNUSED. Contains main.py and various older engine files (driver_engine.py, pathway_engine.py).
- **
avigator_api/**: LEGACY/UNUSED. Contains an older main.py iteration.

## 9. Legacy/Unused Directory Candidates
- ackend/
- 
avigator_api/
- UC07_FINAL_RUNTIME/frontend/
- experiments/, eports/, esults/, step 1 2 3/, powerbi_dashboard/ (Historical ML experimentation artifacts).

## 10. Recommended Final Directory Structure
Based on the evidence, the future reorganization should map:
- UIUX_CTS/ ? **rontend/**
- UC07_FINAL_RUNTIME/backend/ ? **ackend/**
- Data pipelines and model artifacts from scripts/, project_scripts/, and pipeline/ ? **ml/** or **data/**.

## 11. Files That Must Be Preserved
- Everything inside UIUX_CTS/ and UC07_FINAL_RUNTIME/backend/.
- The historical feature database (patient_features.db).
- The provider catalog database (provider_index.db).
- The Synthea raw datasets (data/ or data_improved/).
- The production ML models (models/).

## 12. Files That Can Potentially Be Archived
- UC07_FINAL_RUNTIME/frontend/
- ackend/
- 
avigator_api/
- Jupyter notebooks, old CSV dumps, and temporary outputs generated during hackathon prototyping.

## 13. Files Requiring Further Validation
- care_management/pathway_recommendations.csv (14MB static dump).
- Elements of kg_rag/ (Determine if RAG is actually hooked up to the active backend).

---

### Final Answers
- **"Which exact folder is currently serving the frontend?"**: UIUX_CTS/
- **"Which exact folder is currently serving the backend?"**: UC07_FINAL_RUNTIME/backend/
- **"Which frontend should become the canonical frontend?"**: UIUX_CTS
- **"Which backend should become the canonical backend?"**: UC07_FINAL_RUNTIME/backend
- **"Which directories are duplicates?"**: ackend/ and 
avigator_api/ duplicate the active backend. UC07_FINAL_RUNTIME/frontend/ duplicates the active frontend.
- **"Which files must NOT be touched?"**: UIUX_CTS/*, UC07_FINAL_RUNTIME/backend/*, models/*, data/*.
