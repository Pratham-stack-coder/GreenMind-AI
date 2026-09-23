"""Telemetry router — live metrics and historical data with realistic time-of-day patterns."""

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

# Region-specific CPU base offsets (simulate regional workload differences)
_REGION_OFFSETS = {
    "us-east": 8.0,
    "us-west": 4.0,
    "eu-west": 2.0,
    "ap-southeast": 5.0,
    "ca-central": 1.0,
    "in-north": 6.0,
}


def _business_hour_factor(hour: float, day: int) -> float:
    """Returns a 0–1 scalar representing business-hour load.

    - Peaks at 10:00–16:00 (workday core)
    - Lower overnight (0–7, 20–24)
    - Weekends ~40% of weekday peak
    """
    weekend = 0.4 if day >= 5 else 1.0
    # Double-Gaussian: morning ramp + afternoon sustain
    morning = math.exp(-0.5 * ((hour - 10.0) / 2.5) ** 2)
    afternoon = math.exp(-0.5 * ((hour - 15.0) / 2.5) ** 2)
    diurnal = 0.6 * morning + 0.5 * afternoon
    # Minimum floor (overnight) ~ 0.15
    return max(0.15, diurnal) * weekend


def _generate_live_metrics(provider: str, region: str) -> CloudMetrics:
    now = datetime.now(timezone.utc)
    hour = now.hour + now.minute / 60.0
    day = now.weekday()

    factor = _business_hour_factor(hour, day)
    region_offset = _REGION_OFFSETS.get(region, 0.0)

    # CPU: base 20% + up to +60% during business hours
    cpu_base = 20.0 + factor * 60.0 + region_offset
    # Add realistic noise (micro-burst spikes, cache misses, etc.)
    noise = random.gauss(0, 3.5)
    # Occasional spike (5% chance) to simulate bursty workloads
    if random.random() < 0.05:
        noise += random.uniform(15, 30)
    cpu = round(cpu_base + noise, 1)
    cpu = max(2.0, min(98.0, cpu))

    # Memory: correlates with CPU but with higher baseline and lower variance
    memory_base = 40.0 + factor * 35.0 + random.gauss(0, 2.5)
    memory = round(memory_base, 1)
    memory = max(10.0, min(95.0, memory))

    # Network: correlated with CPU spikes (I/O bound workloads)
    network_base = 150.0 + factor * 650.0
    # Network is proportional to cpu (I/O follows compute)
    network = round(network_base * (0.7 + 0.6 * (cpu / 100)) + random.gauss(0, 40), 1)
    network = max(50.0, min(2000.0, network))

    storage = round(random.uniform(45, 70), 1)

    # Cost: scales with both base provider rate and instantaneous CPU load
    base_cost = _PROVIDER_COSTS.get(provider, 0.192)
    load_multiplier = 1.0 + (cpu / 100.0) * 0.35  # up to +35% at 100% CPU
    cost = round(base_cost * load_multiplier, 4)

    # Carbon: from regional grid intensity × power draw
    intensity = get_carbon_intensity(region, now.hour)["carbon_intensity_gco2_per_kwh"]
    power_kw = 0.35 * load_multiplier  # simplified server power model
    carbon = round(power_kw * intensity, 2)

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
    """Real-time cloud metrics (DEMO: synthetic with realistic patterns; LIVE: replace _generate_live_metrics)."""
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
