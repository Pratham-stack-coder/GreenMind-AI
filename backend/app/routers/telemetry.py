"""Telemetry router — live metrics and historical data with realistic time-of-day patterns.

DATA TRUTH RULE:
- DEMO_MODE=true  : all endpoints return deterministic synthetic data labeled source=DEMO
- DEMO_MODE=false : endpoints route through the provider factory.
  If the provider has valid credentials → source=LIVE_AWS/LIVE_AZURE/LIVE_GCP
  If credentials fail               → source=ERROR (never silently returns fake LIVE data)
  If provider is unconfigured       → source=DEMO  (explicitly labeled)
"""

from __future__ import annotations

import logging
import math
import random
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from ..carbon import get_carbon_intensity
from ..cloud import get_provider
from ..config import get_settings
from ..database import get_telemetry_history, record_telemetry
from ..schemas import CloudMetrics, TelemetryHistoryResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telemetry", tags=["Telemetry"])
settings = get_settings()

# Simulated per-provider base costs (USD/hr) — only used for DEMO mode
_PROVIDER_COSTS = {"aws": 0.192, "azure": 0.184, "gcp": 0.178}
_PROVIDER_REGIONS = {
    "aws": ["us-east", "us-west", "eu-west", "ap-southeast", "ca-central", "in-north"],
    "azure": ["us-east", "eu-west", "ap-southeast"],
    "gcp": ["us-east", "us-west", "eu-west"],
}

# Region-specific CPU base offsets (simulate regional workload differences in DEMO mode)
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
    """Generate deterministic DEMO metrics with realistic time-of-day patterns.

    NOTE: This function is ONLY for DEMO mode. It MUST never be called when
    the system is in LIVE mode with real provider credentials.
    """
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

    # Carbon: from regional grid intensity × power draw (ESTIMATED from DEMO curves)
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
        memory_source="DEMO",
        memory_note="Synthetic DEMO data — configure cloud credentials for live telemetry.",
    )
    record_telemetry(m.model_dump())
    return m


def _provider_metrics_to_cloudmetrics(data: dict, provider: str, region: str) -> CloudMetrics:
    """Normalize a provider.get_metrics() dict to a CloudMetrics schema object."""
    raw_source = data.get("source", "DEMO")
    now_iso = datetime.now(timezone.utc).isoformat()
    return CloudMetrics(
        timestamp=data.get("timestamp", now_iso),
        provider=data.get("provider", provider),
        region=data.get("region", region),
        resource_id=data.get("resource_id"),
        account_id=data.get("account_id"),
        resource_type=data.get("resource_type", "instance"),
        cpu=float(data.get("cpu", 0.0)),
        memory=data.get("memory"),          # may be None (UNAVAILABLE)
        storage=data.get("storage"),        # may be None (UNAVAILABLE)
        network=data.get("network"),        # may be None (UNAVAILABLE)
        network_in=data.get("network_in"),
        network_out=data.get("network_out"),
        cost_usd_per_hour=float(data.get("cost_usd_per_hour", 0.0)),
        carbon_gco2_per_hour=float(data.get("carbon_gco2_per_hour", 0.0)),
        instance_count=int(data.get("instance_count", 1)),
        status=data.get("status", "running"),
        source=raw_source,  # type: ignore[arg-type]
        cost_source=data.get("cost_source"),
        memory_source="UNAVAILABLE" if data.get("memory") is None else data.get("memory_source", raw_source),  # type: ignore[arg-type]
        network_source="UNAVAILABLE" if data.get("network") is None else data.get("network_source", raw_source),
        memory_note=data.get("memory_note"),
        last_updated=data.get("last_updated", now_iso),
    )


@router.get("/live", response_model=CloudMetrics)
def live_metrics(
    provider: str = Query("aws", description="Cloud provider (aws, azure, gcp)"),
    region: str = Query("us-east", description="Region"),
):
    """Real-time cloud metrics.

    DATA TRUTH:
    - DEMO_MODE=true or unconfigured credentials → source=DEMO (clearly labeled)
    - Configured live credentials → source=LIVE_AWS / LIVE_AZURE / LIVE_GCP
    - Credentials configured but API failed → source=ERROR (never falls back to fake LIVE data)
    """
    p = get_provider(provider)

    if p.is_live:
        # Provider has valid credentials → call real API
        try:
            data = p.get_metrics(region)
            m = _provider_metrics_to_cloudmetrics(data, provider, region)
            record_telemetry(m.model_dump())
            logger.info(
                "Live telemetry collected",
                extra={"provider": provider, "region": region, "source": m.source}
            )
            return m
        except Exception as e:
            logger.error(f"Live metrics collection failed for {provider}/{region}: {e}")
            # BUG-006 PREVENTION: Do NOT fall back to DEMO data when LIVE is expected.
            now = datetime.now(timezone.utc)
            err_m = CloudMetrics(
                timestamp=now.isoformat(),
                provider=provider,
                region=region,
                cpu=0.0,
                memory=None,
                storage=None,
                network=None,
                cost_usd_per_hour=0.0,
                carbon_gco2_per_hour=0.0,
                instance_count=0,
                status="error",
                source="ERROR",  # type: ignore[arg-type]
                memory_source="ERROR",  # type: ignore[arg-type]
                memory_note=f"Live metrics collection failed: {type(e).__name__}: {str(e)[:120]}",
                last_updated=now.isoformat(),
            )
            record_telemetry(err_m.model_dump())
            return err_m
    else:
        # Provider is not live (DEMO_MODE or unconfigured) → return correctly labeled DEMO data
        return _generate_live_metrics(provider, region)


@router.get("/live/all")
def live_all():
    """Live metrics from all providers and their primary regions."""
    results = []
    for prov, regions in _PROVIDER_REGIONS.items():
        p = get_provider(prov)
        for region in regions[:2]:  # first 2 per provider to keep response lean
            if p.is_live:
                try:
                    data = p.get_metrics(region)
                    m = _provider_metrics_to_cloudmetrics(data, prov, region)
                except Exception as e:
                    logger.error(f"Failed to collect live metrics for {prov}/{region}: {e}")
                    now = datetime.now(timezone.utc)
                    m = CloudMetrics(
                        timestamp=now.isoformat(),
                        provider=prov,
                        region=region,
                        cpu=0.0,
                        memory=None,
                        storage=None,
                        network=None,
                        cost_usd_per_hour=0.0,
                        carbon_gco2_per_hour=0.0,
                        instance_count=0,
                        status="error",
                        source="ERROR",
                        memory_source="ERROR",
                        memory_note=f"Live collection failed: {e}",
                        last_updated=now.isoformat(),
                    )
            else:
                m = _generate_live_metrics(prov, region)
            record_telemetry(m.model_dump())
            results.append(m)
    return {"providers": results}


@router.get("/history", response_model=TelemetryHistoryResponse)
def telemetry_history(
    provider: str | None = Query(None, description="Filter by cloud provider"),
    region: str | None = Query(None, description="Filter by region"),
    granularity: str = Query("5m", pattern="^(5m|15m|1h|1d)$", description="Aggregation granularity"),
    limit: int = Query(50, ge=1, le=500, description="Max history points"),
):
    """Timestamped telemetry history with multi-cloud filtering and granularity support."""
    entries_raw = get_telemetry_history(limit * 6)
    filtered = []
    for e in entries_raw:
        if provider and e.get("provider", "").lower() != provider.lower():
            continue
        if region and e.get("region", "").lower() != region.lower():
            continue
        filtered.append(e)

    # Step down / sample by granularity
    step = 1
    if granularity == "15m":
        step = 3
    elif granularity == "1h":
        step = 12
    elif granularity == "1d":
        step = 288

    sampled = filtered[::step][:limit]
    entries = [CloudMetrics(**e) for e in sampled]
    dominant_source = entries[0].source if entries else "DEMO"

    return TelemetryHistoryResponse(
        entries=entries,
        count=len(entries),
        provider=provider,
        region=region,
        granularity=granularity,
        source=dominant_source,
    )


async def collect_and_persist_telemetry() -> None:
    """Periodic telemetry collection across configured providers/regions into database."""
    from ..database import persist_telemetry_entry
    from ..cloud import get_provider
    for prov, regions in _PROVIDER_REGIONS.items():
        p = get_provider(prov)
        for region in regions[:1]:
            try:
                if p.is_live:
                    data = p.get_metrics(region)
                    m = _provider_metrics_to_cloudmetrics(data, prov, region)
                else:
                    m = _generate_live_metrics(prov, region)
                await persist_telemetry_entry(m.model_dump())
            except Exception as e:
                logger.debug(f"Background telemetry collection error for {prov}/{region}: {e}")

