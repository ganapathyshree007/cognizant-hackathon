FROM python:3.12-slim
WORKDIR /app
COPY navigator_api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt pandas scikit-learn xgboost joblib
COPY navigator_api /app/navigator_api
COPY model_artifacts /app/model_artifacts
COPY model_runtime /app/model_runtime
COPY kg_rag /app/kg_rag
COPY provider_catalog/provider_catalog.sqlite /app/provider_catalog/provider_catalog.sqlite
COPY safety_engine_output /app/safety_engine_output
ENV NAVIGATOR_PROJECT_ROOT=/app
EXPOSE 8000
CMD ["uvicorn", "navigator_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
