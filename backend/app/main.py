"""
GreenMind AI — Autonomous Green Cloud Operating System
FastAPI backend v2.0

Unified routing:
- All core endpoints exposed under /api/v1/
- Direct root endpoints preserved & mapped for enterprise cloud APIs
  (/, /health, /metrics, /history, /analytics, /predict, /cloud-metrics,
   /predictions, /recommendations, /cost-analysis, /carbon-analysis,
   /agents, /digital-twin/simulate, /copilot/chat, /cloud/providers, /cloud/resources)
"""

from __future__ import annotations

import math
import random
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from . import carbon
from .cloud import get_provider
from .config import get_settings
from .decision_engine import classify_risk, recommend
from .ml import predictor
from .monitoring import (
    PrometheusMiddleware,
    generate_prometheus_metrics,
    track_cloud_collection,
    track_prediction_request,
)
from .routers import (
    agents,
    analytics,
    copilot,
    digital_twin,
    predictions,
    recommendations,
    telemetry,
)
from .schemas import (
    AgentRunRequest,
    AgentRunResponse,
    CloudMetrics,
    CopilotRequest,
    CopilotResponse,
    MetricForecast,
    PredictRequest,
    PredictResponse,
    ScheduleRequest,
    ScheduleResponse,
    SimulationRequest,
    SimulationResult,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: pre-load ML models so first request is immediate."""
    try:
        predictor.model_info()
    except FileNotFoundError:
        pass
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

# Middleware
app.add_middleware(PrometheusMiddleware)
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


# ── Root & System Endpoints ───────────────────────────────────────────────────

@app.get("/", tags=["System"])
def root():
    return {
        "name": "GreenMind AI",
        "title": "Autonomous Green Cloud Operating System",
        "version": settings.app_version,
        "status": "online",
        "demo_mode": settings.demo_mode,
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
        "endpoints": {
            "telemetry": "/api/v1/telemetry/live",
            "predictions": "/api/v1/predictions/forecast",
            "recommendations": "/api/v1/recommendations",
            "agents": "/api/v1/agents/run",
            "digital_twin": "/api/v1/digital-twin/simulate",
            "copilot": "/api/v1/copilot/chat",
            "analytics": "/api/v1/analytics/cost",
        },
    }


@app.get("/health", tags=["System"])
def health():
    return {
        "status": "ok",
        "version": settings.app_version,
        "demo_mode": settings.demo_mode,
        "cloud_mode": "demo" if settings.demo_mode else "live",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "sqlite" if not settings.database_url else "postgresql",
        "redis": bool(settings.redis_url),
        "llm_configured": bool(settings.openai_api_key or settings.gemini_api_key),
    }


# ── Monitoring & Telemetry Endpoints ──────────────────────────────────────────

@app.get("/metrics/prometheus", tags=["Monitoring"])
def metrics_prometheus():
    """Prometheus exposition format metrics for scrapers."""
    content = generate_prometheus_metrics()
    return Response(content=content, media_type="text/plain; version=0.0.4; charset=utf-8")


@app.get("/metrics", tags=["Telemetry"])
def metrics(provider: str = "aws", region: str = "us-east"):
    """Current live metrics from cloud provider."""
    track_cloud_collection()
    p = get_provider(provider)
    return p.get_metrics(region)


@app.get("/history", tags=["Telemetry"])
def history(limit: int = Query(50, le=500)):
    """Recent telemetry history."""
    return telemetry.telemetry_history(limit=limit)


@app.get("/cloud-metrics", response_model=CloudMetrics, tags=["Telemetry"])
def cloud_metrics(region: str = carbon.DEFAULT_REGION, provider: str = "aws"):
    """Cloud metrics endpoint (preserves demo mode compatibility)."""
    track_cloud_collection()
    p = get_provider(provider)
    data = p.get_metrics(region)
    return CloudMetrics(**data)


# ── AI Predictions & Forecasts ────────────────────────────────────────────────

@app.post("/predict", tags=["ML"])
def predict(cpu: float = 45.0, hour: float = 12.0, day_of_week: int = 0):
    """Predict CPU utilization using trained Gradient Boosting model."""
    track_prediction_request()
    try:
        pred = predictor.predict_cpu(cpu, hour, day_of_week)
        return {
            "current_cpu": cpu,
            "predicted_cpu": pred.predicted,
            "delta_pct": pred.delta_pct,
            "anomaly": pred.anomaly,
            "confidence": pred.confidence,
            "risk": classify_risk(pred.predicted),
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/predictions", tags=["ML"])
def get_predictions(provider: str = "aws", region: str = "us-east"):
    """Multi-metric 60-minute forecast across all 5 dimensions."""
    track_prediction_request()
    from .copilot.tools import get_predictions as fetch_preds
    p = get_provider(provider)
    m = p.get_metrics(region)
    return fetch_preds(cpu=m.get("cpu", 50.0))


# ── Analytics & Optimizations ─────────────────────────────────────────────────

@app.get("/analytics", tags=["Analytics"])
def analytics_overview(days: int = Query(7, ge=1, le=90), provider: str = "aws", region: str = "us-east"):
    """Unified analytics combining cost, carbon, and optimization scores."""
    cost = analytics.cost_analytics(days=days)
    carb = analytics.carbon_analytics(days=days, region=region)
    scores = analytics.optimization_scores(provider=provider, region=region)
    return {
        "period_days": days,
        "cost": cost,
        "carbon": carb,
        "scores": scores,
    }


@app.get("/cost-analysis", tags=["Analytics"])
def cost_analysis(days: int = Query(7, ge=1, le=90)):
    """Cost breakdown and top cost drivers."""
    return analytics.cost_analytics(days=days)


@app.get("/carbon-analysis", tags=["Analytics"])
def carbon_analysis(days: int = Query(7, ge=1, le=90), region: str = "us-east"):
    """Carbon emissions breakdown and green window analysis."""
    return analytics.carbon_analytics(days=days, region=region)


@app.get("/recommendations", tags=["Recommendations"])
def get_recommendations(
    provider: str = Query("aws"),
    region: str = Query("us-east"),
    category: str | None = None,
    priority: str | None = None,
):
    """Retrieve optimization recommendations."""
    return recommendations.list_recommendations(
        provider=provider, region=region, category=category, priority=priority
    )


# ── Multi-Agent AI ────────────────────────────────────────────────────────────

@app.get("/agents", tags=["Multi-Agent"])
def get_agents():
    """List registered agents and operational status."""
    return {
        "agents": [
            {"name": "Cost Agent", "id": "cost", "role": "Right-sizing & spend waste elimination", "status": "active"},
            {"name": "Performance Agent", "id": "performance", "role": "Latency & capacity risk protection", "status": "active"},
            {"name": "Sustainability Agent", "id": "sustainability", "role": "Scope 2 carbon reduction & time-shifting", "status": "active"},
            {"name": "Security Agent", "id": "security", "role": "Attack surface & configuration posture", "status": "active"},
            {"name": "Reliability Agent", "id": "reliability", "role": "Multi-AZ redundancy & availability SLA", "status": "active"},
        ],
        "orchestrator": "LangGraph StateGraph",
        "conflict_resolution": "Transparent Multi-Objective Reconciler",
    }


@app.post("/agents/run", response_model=AgentRunResponse, tags=["Multi-Agent"])
def post_agents_run(req: AgentRunRequest):
    """Run full LangGraph multi-agent analysis with transparent conflict resolution."""
    return agents.run_agents(req)


# ── Digital Twin Simulation ───────────────────────────────────────────────────

@app.post("/digital-twin/simulate", response_model=SimulationResult, tags=["Digital Twin"])
def post_digital_twin_simulate(req: SimulationRequest):
    """Simulate infrastructure changes."""
    return digital_twin.simulate(req)


# ── AI Copilot ────────────────────────────────────────────────────────────────

@app.post("/copilot/chat", response_model=CopilotResponse, tags=["AI Copilot"])
async def post_copilot_chat(req: CopilotRequest):
    """Conversational cloud copilot chat grounded in real telemetry and tools."""
    return await copilot.chat(req)


# ── Cloud Provider & Resource Inventory ───────────────────────────────────────

@app.get("/cloud/providers", tags=["Cloud Providers"])
def cloud_providers():
    """List supported cloud providers and connection statuses."""
    aws_p = get_provider("aws")
    azure_p = get_provider("azure")
    gcp_p = get_provider("gcp")
    return {
        "providers": [
            {
                "id": "aws",
                "name": "Amazon Web Services",
                "mode": "LIVE" if aws_p.is_live else "DEMO",
                "regions": ["us-east", "us-west", "eu-west", "ap-southeast", "ca-central", "in-north"],
                "live_metrics_supported": ["CPUUtilization", "NetworkIn", "NetworkOut"],
                "requires_cw_agent": ["MemoryUtilization", "DiskSpaceUtilization"],
            },
            {
                "id": "azure",
                "name": "Microsoft Azure",
                "mode": "LIVE" if azure_p.is_live else "DEMO",
                "regions": ["us-east", "eu-west", "ap-southeast"],
                "live_metrics_supported": ["Percentage CPU", "Network In Total"],
                "requires_cw_agent": [],
            },
            {
                "id": "gcp",
                "name": "Google Cloud Platform",
                "mode": "LIVE" if gcp_p.is_live else "DEMO",
                "regions": ["us-east", "us-west", "eu-west"],
                "live_metrics_supported": ["compute.googleapis.com/instance/cpu/utilization"],
                "requires_cw_agent": [],
            },
        ],
        "default_mode": "DEMO (Zero-config synthetic patterns)",
    }


@app.get("/cloud/resources", tags=["Cloud Providers"])
def cloud_resources(provider: str = Query("aws"), region: str = Query("us-east")):
    """List inventory of cloud resources (VMs, DBs, Storage)."""
    p = get_provider(provider)
    return {
        "provider": provider,
        "region": region,
        "resources": p.get_resources(region),
        "count": len(p.get_resources(region)),
    }


# ── Legacy v1 endpoints (backward compatibility) ──────────────────────────────

@app.get("/api/v1/regions", tags=["System"])
@app.get("/regions", tags=["Legacy"])
def legacy_regions():
    return {"regions": carbon.available_regions()}


@app.get("/api/v1/carbon-curve", tags=["Carbon"])
@app.get("/carbon-curve", tags=["Legacy"])
def legacy_carbon_curve(region: str = carbon.DEFAULT_REGION):
    return {
        "region": region,
        "curve": carbon.get_intensity_curve(region),
        "green_score": carbon.region_green_score(region),
    }


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
