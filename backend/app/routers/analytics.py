"""Analytics router — cost, carbon, and optimization scores."""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

from .. import carbon
from ..schemas import (
    CarbonAnalyticsResponse,
    CarbonDataPoint,
    CostAnalyticsResponse,
    CostDataPoint,
    OptimizationScores,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/cost", response_model=CostAnalyticsResponse)
def cost_analytics(days: int = Query(7, ge=1, le=90)):
    """Cost breakdown over the past N days."""
    now = datetime.now(timezone.utc)
    points: list[CostDataPoint] = []
    total = 0.0
    by_provider = {"aws": 0.0, "azure": 0.0, "gcp": 0.0}

    rng = random.Random(42)
    for i in range(days * 24):
        ts = now - timedelta(hours=days * 24 - i)
        h = ts.hour
        # Daily CPU pattern drives cost
        cpu = 35 + 30 * math.sin((h - 7) / 24 * 2 * math.pi) ** 2
        cost = round(0.192 * (1 + cpu / 200) + rng.uniform(-0.01, 0.01), 4)
        total += cost
        provider = "aws"
        by_provider[provider] += cost
        points.append(CostDataPoint(
            timestamp=ts.isoformat(),
            cost_usd=cost,
            provider=provider,
            region="us-east",
            category="compute",
        ))

    return CostAnalyticsResponse(
        period_days=days,
        total_usd=round(total, 2),
        data_points=points,
        breakdown_by_provider={k: round(v, 2) for k, v in by_provider.items()},
        top_cost_drivers=["EC2 Compute", "Data Transfer", "EBS Storage"],
    )


@router.get("/carbon", response_model=CarbonAnalyticsResponse)
def carbon_analytics(
    days: int = Query(7, ge=1, le=90),
    region: str = Query("us-east"),
):
    """Carbon emissions breakdown over the past N days."""
    now = datetime.now(timezone.utc)
    points: list[CarbonDataPoint] = []
    total = 0.0
    by_region = {region: 0.0}
    green_hours = 0

    _THRESHOLD = 250  # gCO2/kWh — below = "green hour"
    curve = carbon.get_intensity_curve(region)

    for i in range(days * 24):
        ts = now - timedelta(hours=days * 24 - i)
        h = ts.hour
        ci = curve[h]["carbon_intensity_gco2_per_kwh"]
        carbon_val = round(0.35 * ci / 1000, 4)  # kgCO2 estimate
        total += carbon_val
        by_region[region] = by_region.get(region, 0) + carbon_val
        if ci < _THRESHOLD:
            green_hours += 1
        points.append(CarbonDataPoint(
            timestamp=ts.isoformat(),
            carbon_gco2=round(carbon_val * 1000, 2),
            provider="aws",
            region=region,
            intensity_gco2_per_kwh=ci,
        ))

    total_hours = days * 24
    green_pct = round(green_hours / total_hours * 100, 1) if total_hours else 0

    return CarbonAnalyticsResponse(
        period_days=days,
        total_gco2=round(total * 1000, 2),
        data_points=points,
        breakdown_by_region={k: round(v * 1000, 2) for k, v in by_region.items()},
        green_hours_pct=green_pct,
    )


@router.get("/score", response_model=OptimizationScores)
def optimization_scores(
    provider: str = Query("aws"),
    region: str = Query("us-east"),
):
    """Return 0–100 optimization scores per dimension."""
    # Import here to avoid circular
    from ..routers.telemetry import _generate_live_metrics
    m = _generate_live_metrics(provider, region)

    cpu = m.cpu
    memory = m.memory
    ci = carbon.get_carbon_intensity(region, datetime.now(timezone.utc).hour)["carbon_intensity_gco2_per_kwh"]

    cost_score = max(0, 100 - int((cpu < 30) * 25 + (cpu < 15) * 25))
    perf_score = max(0, 100 - int((cpu > 75) * 20 + (cpu > 90) * 30 + (memory > 85) * 25))
    sus_score = max(0, round(100 - (ci - 79) / (720 - 79) * 100))
    sec_score = 75  # demo static — needs live IAM scan
    rel_score = 70  # demo static — needs AZ info

    overall = round((cost_score + perf_score + sus_score + sec_score + rel_score) / 5)
    trend = "improving" if overall >= 70 else ("stable" if overall >= 50 else "declining")

    return OptimizationScores(
        overall=overall,
        cost=cost_score,
        performance=perf_score,
        sustainability=sus_score,
        security=sec_score,
        reliability=rel_score,
        trend=trend,
    )
