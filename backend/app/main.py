"""
GreenMind AI backend.

Endpoints:
  GET  /health                    liveness check
  GET  /cloud-metrics              current (demo) cloud metrics
  POST /predict                    CPU forecast + risk level
  POST /schedule-recommendation    carbon+cost aware run recommendation
  GET  /carbon-curve                24h carbon intensity curve for a region
  GET  /regions                     available demo regions

Everything here runs in DEMO mode: /cloud-metrics returns synthetic values
and /carbon-curve returns an illustrative lookup table (see app/carbon.py).
Nothing in this API claims to be live cloud telemetry.
"""

import random
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import carbon, decision_engine
from .ml import predictor
from .schemas import (
    CloudMetrics,
    PredictRequest,
    PredictResponse,
    ScheduleRequest,
    ScheduleResponse,
)

app = FastAPI(
    title="GreenMind AI",
    description="Carbon-and-cost-aware cloud scheduling (demo backend).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before any real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/regions")
def regions():
    return {"regions": carbon.available_regions()}


@app.get("/carbon-curve")
def carbon_curve(region: str = carbon.DEFAULT_REGION):
    return {"region": region, "curve": carbon.get_intensity_curve(region)}


@app.get("/cloud-metrics", response_model=CloudMetrics)
def cloud_metrics(region: str = carbon.DEFAULT_REGION):
    """
    DEMO cloud metrics. Replace with a real collector (e.g. an AWS CloudWatch
    poller) that returns the same schema to go live -- nothing downstream of
    this endpoint needs to change.
    """
    now = datetime.now(timezone.utc)
    hour = now.hour + now.minute / 60.0
    base_cpu = 35 + 30 * max(0, __import__("math").sin((hour - 7) / 24 * 6.28)) ** 2
    return CloudMetrics(
        timestamp=now.isoformat(),
        region=region,
        cpu=round(base_cpu + random.uniform(-4, 4), 1),
        memory=round(random.uniform(40, 75), 1),
        storage=round(random.uniform(30, 60), 1),
        network=round(random.uniform(300, 800), 1),
        source="DEMO",
    )


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    try:
        predicted = predictor.predict_future_cpu(
            cpu=req.cpu,
            hour=req.hour,
            day_of_week=req.day_of_week,
            cpu_rolling_avg_1h=req.cpu_rolling_avg_1h,
            cpu_rolling_std_1h=req.cpu_rolling_std_1h,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    info = predictor.model_info()
    mae = info.get("gradient_boosting", {}).get("mae")

    return PredictResponse(
        current_cpu=req.cpu,
        predicted_cpu=round(predicted, 2),
        risk=decision_engine.classify_risk(predicted),
        model_mae=mae,
    )


@app.post("/schedule-recommendation", response_model=ScheduleResponse)
def schedule_recommendation(req: ScheduleRequest):
    rec = decision_engine.recommend(
        predicted_cpu=req.predicted_cpu,
        current_hour=req.current_hour,
        region=req.region,
        job_duration_hours=req.job_duration_hours,
        deferrable=req.deferrable,
        max_defer_hours=req.max_defer_hours,
    )
    return ScheduleResponse(**rec.__dict__)
