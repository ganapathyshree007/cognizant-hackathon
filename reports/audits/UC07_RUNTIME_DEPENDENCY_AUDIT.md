# UC07 Runtime Dependency Audit

## 1. Final Runtime Files

The final runtime strictly consists of the FastAPI orchestrator (`api.py`), the React UI, the two modular engines (Safety & Provider), the trained risk model, and the two pre-indexed SQLite databases.

### Required Model
- `UC07_SYNTHEA_STEP4_BEST_MODEL.joblib`
  - **Component**: Backend Orchestrator (Step 4 Risk Scoring)
  - **Reference**: Loaded in `care_manager_app/backend/api.py` via `joblib.load()`
  - **Dependency**: Requires `lightgbm` and `scikit-learn` (for `CalibratedClassifierCV` wrapper). It includes its own preprocessing pipeline but requires the 43 historical features to be passed into `.predict_proba()`.
  - **What breaks if removed**: Step 4 API calls will return a `500 MODEL_ERROR`, causing the orchestration flow to fail.

### Required Databases
- `patient_features.db`
  - **Component**: Backend Orchestrator
  - **Reference**: Queried by `api.py` (`get_real_patient_features()`)
  - **Dependency**: Contains the actual historical feature matrix used by the LightGBM model. 
  - **What breaks if removed**: API will return `DATA_UNAVAILABLE`. The original CSV (`UC07_SYNTHEA_STEP4_HISTORICAL_FEATURES.csv`) is **NOT** needed at runtime since the engine strictly queries the DB.
- `provider_index.db`
  - **Component**: Backend Orchestrator
  - **Reference**: Queried by `api.py` (`get_real_providers_by_specialty()`)
  - **Dependency**: Contains the merged Synthea providers, DAC attributes, Quality scores, and Utilization volume.
  - **What breaks if removed**: Step 7 provider matching will fail and return `NO_PROVIDER_MATCH`.

### Required Backend Files
- `care_manager_app/backend/api.py`
  - **Component**: Main Orchestrator
  - **Reference**: The entry point for the REST API.
- `safety_gate_engine.py`
  - **Component**: Step 5 Module
  - **Reference**: Imported by `api.py` (`from safety_gate_engine import SafetyGateEngine`)
  - **What breaks if removed**: Step 5 safety gate evaluation fails, halting pipeline.
- `provider_matching_engine.py`
  - **Component**: Step 7 Module
  - **Reference**: Imported by `api.py` (`from provider_matching_engine import ProviderMatchingPrototype`)
  - **What breaks if removed**: Step 7 ranking algorithm fails.
- `UC07_CARE_MANAGER_AUDIT_TRAIL.csv`
  - **Component**: Human-in-the-loop Audit Log
  - **Reference**: Appended to by `api.py` `/api/audit` route.

### Required Frontend Files
- `care_manager_app/frontend/src/App.jsx`
- `care_manager_app/frontend/src/main.jsx`
- `care_manager_app/frontend/src/App.css`
- `care_manager_app/frontend/src/index.css`
- `care_manager_app/frontend/index.html`
- `care_manager_app/frontend/package.json`
- `care_manager_app/frontend/tsconfig.json`
  - **Component**: Care Manager Dashboard

## 2. Dependencies

### Required Python Packages
- `fastapi`
- `uvicorn`
- `pydantic`
- `pandas`
- `numpy`
- `scikit-learn`
- `lightgbm`
- `joblib`

### Required npm Packages
- `vite`
- `react` (Implied in code, required for runtime)
- `react-dom` (Implied in code)

## 3. Classifications

### Files NOT required at runtime
- `UC07_SYNTHEA_STEP4_HISTORICAL_FEATURES.csv` (Features are served from SQLite cache)
- `sources/` and `step4_raw/` directories (Raw data is not read at runtime)

### Files that can be archived
- `benchmark_step4_models.py`, `build_step4_features.py`, `build_real_data_indexes.py` (Data and models are already built).
- Experimental models (`experimental_*.joblib`, `synthea_benchmark_*.joblib`).

### Files that are duplicates
- Older `.joblib` models not selected for the final architecture (e.g. `benchmark_random_forest.joblib`).

### Files that MUST NOT be deleted
- **Raw Data**: `sources/`, `step4_raw/`
- **Validated Datasets/DBs**: `patient_features.db`, `provider_index.db`, `UC07_SYNTHEA_STEP4_HISTORICAL_FEATURES.csv` (Need for future retraining)
- **Reports**: All `*.md` audit and gap analysis reports
- **Source Code**: Even if not run at runtime, keeping pipeline building scripts is critical for reproducibility.

## 4. Exact Startup Commands
**Backend:**
```bash
cd D:/cognizant-hackathon-main/care_manager_app/backend
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd D:/cognizant-hackathon-main/care_manager_app/frontend
npm install react react-dom
npm install
npm run dev
```
