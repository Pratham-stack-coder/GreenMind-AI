"""Telemetry router — live metrics and historical data."""

from __future__ import annotations

import math
import random
from datetime import datetime, timezone

from fastapi import APIRouter, Query

from ..carbon import get_carbon_intensity
from ..database import get_telemetry_history, record_telemetry
from ..schemas import CloudMetrics, TelemetryHistoryResponse

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])

# Simulated per-provider base costs (USD/hr)
_PROVIDER_COSTS = {"aws": 0.192, "azure": 0.184, "gcp": 0.178}
_PROVIDER_REGIONS = {
    "aws": ["us-east", "us-west", "eu-west", "ap-southeast", "ca-central", "in-north"],
    "azure": ["us-east", "eu-west", "ap-southeast"],
    "gcp": ["us-east", "us-west", "eu-west"],
}


def _generate_live_metrics(provider: str, region: str) -> CloudMetrics:
    now = datetime.now(timezone.utc)
    hour = now.hour + now.minute / 60.0
    day = now.weekday()
    base_cpu = 35 + 30 * max(0, math.sin((hour - 7) / 24 * 6.28)) ** 2
    weekend = 0.7 if day >= 5 else 1.0
    cpu = round(base_cpu * weekend + random.uniform(-5, 5), 1)
    cpu = max(2.0, min(98.0, cpu))

    memory = round(45 + 15 * math.sin((hour - 8) / 24 * 2 * math.pi) ** 2 + random.uniform(-3, 3), 1)
    memory = max(10.0, min(95.0, memory))

    network = round(300 + 400 * math.sin((hour - 9) / 24 * 2 * math.pi) ** 2 * weekend + random.uniform(-50, 50), 1)
    network = max(50.0, min(2000.0, network))

    storage = round(random.uniform(45, 70), 1)
    base_cost = _PROVIDER_COSTS.get(provider, 0.192)
    cost = round(base_cost * (1 + cpu / 200), 4)

    intensity = get_carbon_intensity(region, now.hour)["carbon_intensity_gco2_per_kwh"]
    carbon = round(0.35 * 0.25 * intensity, 2)  # 15-min window estimate

    m = CloudMetrics(
        timestamp=now.isoformat(),
        provider=provider,
        region=region,
        cpu=cpu,
        memory=memory,
        storage=storage,
        network=network,
        cost_usd_per_hour=cost,
        carbon_gco2_per_hour=carbon,
        instance_count=random.choice([1, 1, 1, 2, 3]),
        source="DEMO",
    )
    record_telemetry(m.model_dump())
    return m


@router.get("/live", response_model=CloudMetrics)
def live_metrics(
    provider: str = Query("aws", description="Cloud provider"),
    region: str = Query("us-east", description="Region"),
):
    """Real-time cloud metrics (DEMO: synthetic; LIVE: replace _generate_live_metrics)."""
    return _generate_live_metrics(provider, region)


@router.get("/live/all")
def live_all():
    """Live metrics from all providers and their primary regions."""
    results = []
    for provider, regions in _PROVIDER_REGIONS.items():
        for region in regions[:2]:  # first 2 per provider to keep response lean
            results.append(_generate_live_metrics(provider, region))
    return {"providers": results}


@router.get("/history", response_model=TelemetryHistoryResponse)
def telemetry_history(limit: int = Query(50, le=500)):
    """Recent telemetry history (in-memory ring buffer)."""
    entries_raw = get_telemetry_history(limit)
    entries = [CloudMetrics(**e) for e in entries_raw]
    return TelemetryHistoryResponse(entries=entries, count=len(entries))
