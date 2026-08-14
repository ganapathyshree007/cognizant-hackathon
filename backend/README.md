# Operational backend

Run with `NAVIGATOR_API_KEY` set to a secret and `NAVIGATOR_PROJECT_ROOT=C:\COGNIZANT HACKATHON`.

`python -m uvicorn main:app --app-dir C:\COGNIZANT HACKATHON\backend --host 127.0.0.1 --port 8000`

All `/v1` endpoints require the `X-API-Key` header. The backend keeps intervention, outcome, and audit records in `backend_state.sqlite`.
