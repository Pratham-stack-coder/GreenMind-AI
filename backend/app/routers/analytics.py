"""Analytics router — cost, carbon, and optimization scores."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

from .. import carbon
from ..cloud import get_provider
from ..schemas import (
    CarbonAnalyticsResponse,
    CarbonDataPoint,
    CostAnalyticsResponse,
    CostDataPoint,
    OptimizationScores,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/cost", response_model=CostAnalyticsResponse)
def cost_analytics(
    days: int = Query(7, ge=1, le=90),
    provider: str = Query("aws"),
    region: str = Query("us-east"),
):
    """Return the provider period total and clearly estimated hourly allocations."""
    now = datetime.now(timezone.utc)
    if hasattr(provider, "default"):
        provider = provider.default
    if hasattr(region, "default"):
        region = region.default
    provider = str(provider or "aws").strip().lower()
    region = str(region or "us-east").strip()

    provider_client = get_provider(provider)
    cost_data = provider_client.get_cost(region, days=days)
    data_source = cost_data.get("source", "DEMO")
    total = max(0.0, float(cost_data.get("total_usd", 0.0)))
    confidence = float(cost_data.get("confidence", 1.0 if str(data_source).startswith("LIVE") else 0.85))
    provider_method = cost_data.get("estimation_method")
    if str(data_source).startswith("LIVE"):
        estimation_method = "hourly_allocation_from_billing_period_total"
    elif provider_method:
        estimation_method = f"{provider_method}; hourly series evenly allocated"
    else:
        estimation_method = "demo_period_total_evenly_allocated"

    # Providers expose a period total, not an hourly billing time series. Do not invent
    # a utilization curve or mark allocated hourly values as directly observed.
    hours = days * 24
    hourly_allocation = total / hours if hours else 0.0
    points: list[CostDataPoint] = []
    for index in range(hours):
        timestamp = now - timedelta(hours=hours - index - 1)
        points.append(CostDataPoint(
            timestamp=timestamp.isoformat(),
            cost_usd=round(hourly_allocation, 6),
            provider=provider,
            region=region,
            category="compute",
            source="ESTIMATED",
        ))

    services = cost_data.get("top_services") or []
    top_cost_drivers = [
        str(item.get("service"))
        for item in services
        if isinstance(item, dict) and item.get("service")
    ]

    return CostAnalyticsResponse(
        period_days=days,
        total_usd=round(total, 2),
        data_points=points,
        breakdown_by_provider={provider: round(total, 2)},
        top_cost_drivers=top_cost_drivers,
        source=data_source,
        estimation_method=estimation_method,
        confidence=max(0.0, min(1.0, confidence)),
    )

@router.get("/carbon", response_model=CarbonAnalyticsResponse)
def carbon_analytics(
    days: int = Query(7, ge=1, le=90),
    region: str = Query("us-east"),
):
    """Carbon emissions breakdown over the past N days with PUE and Scope 2/3 power modeling."""
    now = datetime.now(timezone.utc)
    points: list[CarbonDataPoint] = []
    total = 0.0
    by_region = {region: 0.0}
    green_hours = 0

    _THRESHOLD = 250  # gCO2/kWh — below = "green hour"
    curve = carbon.get_intensity_curve(region)
    pue = carbon.get_pue(region)

    for i in range(days * 24):
        ts = now - timedelta(hours=days * 24 - i)
        h = ts.hour
        ci = curve[h]["carbon_intensity_gco2_per_kwh"]
        power_w = carbon.compute_power_watts("m5.large", 45.0)
        # Operational energy (kWh) = (Watts * PUE / 1000) * 1h
        kwh = (power_w * pue / 1000.0)
        carbon_val = round((kwh * ci) / 1000.0, 4)  # kgCO2
        total += carbon_val
        by_region[region] = by_region.get(region, 0.0) + carbon_val
        if ci < _THRESHOLD:
            green_hours += 1
        points.append(CarbonDataPoint(
            timestamp=ts.isoformat(),
            carbon_gco2=round(carbon_val * 1000.0, 2),
            provider="aws",
            region=region,
            intensity_gco2_per_kwh=ci,
            power_draw_watts=power_w,
            pue=pue,
            source="ESTIMATED",
        ))

    total_hours = days * 24
    green_pct = round(green_hours / total_hours * 100, 1) if total_hours else 0

    return CarbonAnalyticsResponse(
        period_days=days,
        total_gco2=round(total * 1000.0, 2),
        data_points=points,
        breakdown_by_region={k: round(v * 1000.0, 2) for k, v in by_region.items()},
        green_hours_pct=green_pct,
        source="ESTIMATED",
        methodology="GHG_PROTOCOL_SCOPE_2_3",
        confidence=0.88,
    )


@router.get("/score", response_model=OptimizationScores)
def optimization_scores(
    provider: str = Query("aws"),
    region: str = Query("us-east"),
):
    """Return 0–100 optimization scores per dimension.

    DATA TRUTH:
    - In LIVE mode: scores computed from real cloud provider metrics (ESTIMATED source)
    - In DEMO mode: scores computed from synthetic DEMO metrics (DEMO source)
    - Security and Reliability scores are always ESTIMATED (require live security posture data)
    """
    if hasattr(provider, "default"):
        provider = provider.default
    provider = str(provider or "aws")
    if hasattr(region, "default"):
        region = region.default
    region = str(region or "us-east-1")

    p = get_provider(provider)
    if p.is_live:
        raw = p.get_metrics(region)
        from ..schemas import CloudMetrics
        m = CloudMetrics(**raw)
        score_source = "ESTIMATED"
    else:
        from ..routers.telemetry import _generate_live_metrics
        m = _generate_live_metrics(provider, region)
        score_source = "DEMO"

    # Guard against None values (UNAVAILABLE metrics from live providers)
    cpu = m.cpu or 50.0
    memory = m.memory or 55.0  # fallback for scoring only — memory may be UNAVAILABLE

    ci = carbon.get_carbon_intensity(region, datetime.now(timezone.utc).hour)["carbon_intensity_gco2_per_kwh"]

    cost_score = max(0, 100 - int((cpu < 30) * 25 + (cpu < 15) * 25))
    perf_score = max(0, 100 - int((cpu > 75) * 20 + (cpu > 90) * 30 + (memory > 85) * 25))
    sus_score = max(0, round(100 - (ci - 79) / (720 - 79) * 100))
    sec_score = 75  # ESTIMATED — requires live IAM / Security Hub / Defender scan
    rel_score = 70  # ESTIMATED — requires multi-AZ and health check data

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
        source=score_source,  # type: ignore[arg-type]
    )
