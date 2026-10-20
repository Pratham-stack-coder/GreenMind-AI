"""Analytics router — cost, carbon, and optimization scores."""

from __future__ import annotations

import math
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
def cost_analytics(days: int = Query(7, ge=1, le=90), provider: str = Query("aws"), region: str = Query("us-east")):
    """Cost breakdown over the past N days.

    DATA TRUTH:
    - If provider is LIVE with Cost Explorer access: returns real billing period total
    - If billing data is UNAVAILABLE: reports total_usd=None and source="UNAVAILABLE"
    - Hourly data points represent even allocation of the period total, marked ESTIMATED
    """
    now = datetime.now(timezone.utc)

    if hasattr(provider, "default"):
        provider = provider.default
    provider = str(provider or "aws").strip().lower()
    if hasattr(region, "default"):
        region = region.default
    region = str(region or "us-east").strip()

    provider_client = get_provider(provider)
    cost_data = provider_client.get_cost(region, days=days)
    data_source = cost_data.get("source", "DEMO")
    raw_total = cost_data.get("total_usd")
    if data_source == "UNAVAILABLE" or raw_total is None:
        return CostAnalyticsResponse(
            period_days=days,
            total_usd=None,
            data_points=[],
            breakdown_by_provider={},
            top_cost_drivers=[],
            source="UNAVAILABLE",
            estimation_method=None,
            confidence=0.0,
        )
    total = max(0.0, float(raw_total))
    confidence = float(cost_data.get("confidence", 1.0 if str(data_source).startswith("LIVE") else 0.85))
    provider_method = cost_data.get("estimation_method")
    if str(data_source).startswith("LIVE"):
        estimation_method = "hourly_allocation_from_billing_period_total"
    elif provider_method:
        estimation_method = f"{provider_method}; hourly series evenly allocated"
    else:
        estimation_method = "demo_period_total_evenly_allocated"

    # Providers expose a period total, not an hourly billing time series. Do not invent
    # a fake utilization curve or mark allocated hourly values as directly observed.
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
    provider: str = Query("aws"),
):
    """Carbon emissions breakdown over the past N days with PUE and Scope 2/3 power modeling."""
    now = datetime.now(timezone.utc)
    points: list[CarbonDataPoint] = []
    total = 0.0
    by_region = {region: 0.0}
    green_hours = 0
    norm_provider = str(provider or "aws").strip().lower()

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
            provider=norm_provider,
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
        assumptions="Estimated regional emissions for a reference m5.large workload at 45% CPU; not measured workload emissions.",
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

    from ..services.scoring import compute_optimization_scores
    from .recommendations import get_user_simulation_state

    sim_state = get_user_simulation_state(provider=provider, region=region)

    p = get_provider(provider)
    if p.is_live:
        raw = p.get_metrics(region)
        from ..schemas import CloudMetrics
        m = CloudMetrics(**raw)
        score_source = "ESTIMATED"
    else:
        if sim_state and sim_state.get("baseline_metrics"):
            m = sim_state["baseline_metrics"]
        else:
            from ..routers.telemetry import _generate_live_metrics
            m = _generate_live_metrics(provider, region)
        score_source = "DEMO"

    # Calculate baseline scores using single documented scoring service
    baseline_scores = compute_optimization_scores(
        m,
        region=region,
        source=score_source,
    )

    # If the user has active simulated optimizations, return projected simulated score
    sim_state = get_user_simulation_state(provider=provider, region=region)
    if sim_state and sim_state.get("simulated_recommendations"):
        sim_metrics = sim_state.get("simulated_metrics")
        sim_baseline = sim_state.get("baseline_score")
        if sim_baseline is None:
            sim_baseline = baseline_scores.overall
        if sim_metrics is not None:
            return compute_optimization_scores(
                sim_metrics,
                region=region,
                source="SIMULATED",
                is_simulated=True,
                baseline_overall=sim_baseline,
            )

    return baseline_scores
