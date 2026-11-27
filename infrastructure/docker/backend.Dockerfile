FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    ML_MODEL_ARTIFACT_PATH=/app/ml/artifacts/error_classifier_v1.joblib

WORKDIR /app

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

COPY backend/pyproject.toml /app/pyproject.toml
COPY backend/app /app/app
COPY ml /app/ml

RUN pip install --upgrade pip && pip install .

USER appuser

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --no-proxy-headers"]
