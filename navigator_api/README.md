# Avoidable ED Navigator API

Run locally from `C:\COGNIZANT HACKATHON`:

`set PYTHONPATH=C:\COGNIZANT HACKATHON\model_runtime\python_packages`

`C:\Users\ganap\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m uvicorn navigator_api.main:app --host 127.0.0.1 --port 8000`

Endpoints:

- `GET /health`
- `GET /v1/cms/cases/{case_id}/review`
- `GET /v1/synthea/safety-cases/{encounter_id}`
- `GET /v1/providers/search?pathway=PRIMARY_CARE&state=PR`

The service is decision support only. It does not autonomously triage, diagnose, redirect emergency care, or join CMS and Synthea members.
