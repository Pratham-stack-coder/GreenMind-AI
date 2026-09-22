"""
GreenMind AI — Autonomous Green Cloud Operating System
FastAPI backend v2.0

All endpoints versioned under /api/v1/
Legacy v1 endpoints preserved at root for backward compatibility.
"""

from __future__ import annotations

import random
import math
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from . import carbon
from .schemas import CloudMetrics, PredictResponse, ScheduleRequest, ScheduleResponse, MetricForecast
from .decision_engine import classify_risk, recommend
from .ml import predictor
from .routers import telemetry, predictions, recommendations, agents, digital_twin, analytics, copilot

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: pre-load ML models so first request isn't slow."""
    try:
        predictor.model_info()  # triggers _load for cpu model
    except FileNotFoundError:
        pass  # train.py hasn't been run yet — endpoints will return 503
    yield


app = FastAPI(
    title="GreenMind AI",
    description=(
        "Autonomous Green Cloud Operating System — "
        "AI-powered cloud management with cost, performance, sustainability, "
        "security, and reliability intelligence."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins + ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API v1 routers ─────────────────────────────────────────────────────────────
PREFIX = "/api/v1"
app.include_router(telemetry.router, prefix=PREFIX)
app.include_router(predictions.router, prefix=PREFIX)
app.include_router(recommendations.router, prefix=PREFIX)
app.include_router(agents.router, prefix=PREFIX)
app.include_router(digital_twin.router, prefix=PREFIX)
app.include_router(analytics.router, prefix=PREFIX)
app.include_router(copilot.router, prefix=PREFIX)


# ── Health & system ───────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health():
    return {
        "status": "ok",
        "version": settings.app_version,
        "demo_mode": settings.demo_mode,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/regions", tags=["System"])
def regions():
    return {"regions": carbon.available_regions()}


@app.get("/api/v1/carbon-curve", tags=["Carbon"])
def carbon_curve(region: str = carbon.DEFAULT_REGION):
    return {
        "region": region,
        "curve": carbon.get_intensity_curve(region),
        "green_score": carbon.region_green_score(region),
    }


# ── Legacy v1 endpoints (backward-compatible) ─────────────────────────────────

@app.get("/regions", tags=["Legacy"])
def legacy_regions():
    return {"regions": carbon.available_regions()}


@app.get("/carbon-curve", tags=["Legacy"])
def legacy_carbon_curve(region: str = carbon.DEFAULT_REGION):
    return {"region": region, "curve": carbon.get_intensity_curve(region)}


@app.get("/cloud-metrics", response_model=CloudMetrics, tags=["Legacy"])
def legacy_cloud_metrics(region: str = carbon.DEFAULT_REGION):
    now = datetime.now(timezone.utc)
    hour = now.hour + now.minute / 60.0
    base_cpu = 35 + 30 * max(0, math.sin((hour - 7) / 24 * 6.28)) ** 2
    return CloudMetrics(
        timestamp=now.isoformat(),
        region=region,
        cpu=round(base_cpu + random.uniform(-4, 4), 1),
        memory=round(random.uniform(40, 75), 1),
        storage=round(random.uniform(30, 60), 1),
        network=round(random.uniform(300, 800), 1),
        source="DEMO",
    )


@app.post("/predict", tags=["Legacy"])
def legacy_predict(cpu: float = 45.0, hour: float = 12.0, day_of_week: int = 0):
    try:
        pred = predictor.predict_cpu(cpu, hour, day_of_week)
        return {
            "current_cpu": cpu,
            "predicted_cpu": pred.predicted,
            "risk": classify_risk(pred.predicted),
        }
    except FileNotFoundError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/schedule-recommendation", response_model=ScheduleResponse, tags=["Legacy"])
def legacy_schedule(req: ScheduleRequest):
    rec = recommend(
        predicted_cpu=req.predicted_cpu,
        current_hour=req.current_hour,
        region=req.region,
        job_duration_hours=req.job_duration_hours,
        deferrable=req.deferrable,
        max_defer_hours=req.max_defer_hours,
    )
    return ScheduleResponse(**rec.__dict__)
