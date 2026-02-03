"""FastAPI service for cats vs dogs inference."""

from __future__ import annotations

import os
import time
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from cats_dogs.predict import ModelLoadError, PredictionResult, load_model_bundle, predict_bytes

APP_NAME = "cats-dogs-api"
MODEL_PATH = Path(os.getenv("MODEL_PATH", "artifacts/model/model.pkl"))

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "http_status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
)

app = FastAPI(title="Cats vs Dogs Classifier", version="0.1.0")

MODEL_BUNDLE = None
MODEL_LOAD_ERROR: str | None = None


@app.middleware("http")
async def record_metrics(request, call_next):
    start_time = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        endpoint = request.url.path
        REQUEST_COUNT.labels(request.method, endpoint, str(status_code)).inc()
        REQUEST_LATENCY.labels(request.method, endpoint).observe(time.perf_counter() - start_time)


@app.on_event("startup")
def load_model() -> None:
    global MODEL_BUNDLE, MODEL_LOAD_ERROR
    try:
        MODEL_BUNDLE = load_model_bundle(MODEL_PATH)
        MODEL_LOAD_ERROR = None
    except (ModelLoadError, Exception) as exc:
        MODEL_BUNDLE = None
        MODEL_LOAD_ERROR = str(exc)


def _require_model() -> None:
    if MODEL_BUNDLE is None:
        message = MODEL_LOAD_ERROR or "Model not loaded."
        raise HTTPException(status_code=503, detail=message)


@app.get("/health")
def health() -> Response:
    if MODEL_BUNDLE is None:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "error": MODEL_LOAD_ERROR or "Model not loaded."},
        )

    bundle = MODEL_BUNDLE
    return JSONResponse(
        content={
            "status": "ok",
            "app": APP_NAME,
            "model_path": str(MODEL_PATH),
            "model_created_at": bundle.created_at,
            "mlflow_run_id": bundle.mlflow_run_id,
            "schema_version": bundle.schema_version,
            "versions": bundle.versions,
            "build_info": bundle.build_info,
            "class_mapping": bundle.class_to_index,
        }
    )


@app.post("/predict")
async def predict(file: UploadFile = File(...)) -> dict[str, float | str]:
    _require_model()
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")
    payload = await file.read()
    try:
        result: PredictionResult = predict_bytes(MODEL_BUNDLE, payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image payload: {exc}") from exc
    return {"label": result.label, "probability": result.probability}


@app.get("/metrics")
def metrics() -> Response:
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
