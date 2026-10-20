"""Digital Twin router — simulate infrastructure changes before applying."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter

from .. import carbon
from ..decision_engine import INSTANCE_COSTS
from ..digital_twin.schemas import ScenarioSimulationResult, SimulationScenarioRequest
from ..schemas import SimulationMetrics, SimulationRequest, SimulationResult

router = APIRouter(prefix="/digital-twin", tags=["Digital Twin"])

_INSTANCE_KWH = {
    "t3.micro": 0.04, "t3.small": 0.08, "t3.medium": 0.15,
    "m5.large": 0.35, "m5.xlarge": 0.65, "m5.2xlarge": 1.2,
    "c5.large": 0.30, "c5.xlarge": 0.55,
    "r5.large": 0.40, "r5.xlarge": 0.75,
}


def _compute_metrics(
    cpu: float, memory: float | None, instance_type: str, count: int, region: str, hours: float
) -> SimulationMetrics:
    from datetime import datetime, timezone
    hour = datetime.now(timezone.utc).hour
    ci = carbon.get_carbon_intensity(region, hour)["carbon_intensity_gco2_per_kwh"]
    kwh = _INSTANCE_KWH.get(instance_type, 0.35)
    cost_hr = INSTANCE_COSTS.get(instance_type, 0.192) * count
    carbon_hr = round(kwh * ci * count, 2)
    monthly_cost = round(cost_hr * 24 * 30, 2)
    monthly_carbon_kg = round(carbon_hr * 24 * 30 / 1000, 3)

    # ── M/M/1 Queuing Theory Latency Modeling ──────────────────────────────
    # Base service time inversely proportional to compute power
    base_service_ms = 18.0 * (0.35 / max(kwh, 0.05))
    rho = min(0.96, max(0.05, cpu / 100.0))
    expected_resp_ms = base_service_ms / (1.0 - rho)
    p95_latency = round(expected_resp_ms * 1.85, 1)
    p99_latency = round(expected_resp_ms * 2.95, 1)

    # ── Multi-Factor Quantitative Risk Index (0-100) ────────────────────────
    risk_factors: list[str] = []
    base_risk = 10.0

    if cpu > 80:
        base_risk += (cpu - 75) * 2.5
        risk_factors.append(f"High CPU saturation ({cpu}%) elevates throttling risk")
    elif cpu < 20:
        base_risk += 5.0
        risk_factors.append("Low utilization indicates over-provisioning financial risk")

    if memory and memory > 85:
        base_risk += 25.0
        risk_factors.append(f"Memory deficit ({memory}%) increases OOM killer risk")

    if count == 1:
        base_risk += 20.0
        risk_factors.append("Single instance deployment topology lacks HA redundancy")
    elif count > 8:
        base_risk += 5.0
        risk_factors.append("Large cluster count increases inter-node network synchronization overhead")

    risk_score = round(max(5.0, min(95.0, base_risk)), 1)
    if risk_score >= 75:
        risk_level = "critical"
    elif risk_score >= 50:
        risk_level = "high"
    elif risk_score >= 25:
        risk_level = "medium"
    else:
        risk_level = "low"

    return SimulationMetrics(
        cpu=cpu,
        memory=memory,
        cost_usd_per_hour=round(cost_hr, 4),
        carbon_gco2_per_hour=carbon_hr,
        monthly_cost_usd=monthly_cost,
        monthly_carbon_kgco2=monthly_carbon_kg,
        p95_latency_ms=p95_latency,
        p99_latency_ms=p99_latency,
        risk_score=risk_score,
        risk_level=risk_level,
        risk_factors=risk_factors,
        source="SIMULATED",
    )


@router.post("/simulate", response_model=SimulationResult)
def simulate(req: SimulationRequest):
    """Simulate one or more infrastructure changes and return before/after impact.

    DATA TRUTH:
    - Output source is always strictly SIMULATED
    - Baseline source reflects true metric source (LIVE or DEMO)
    """
    m = req.baseline_metrics
    current_instance = "m5.xlarge"  # demo default
    count = m.instance_count
    region = m.region
    warnings: list[str] = []

    # Before state
    before = _compute_metrics(m.cpu, m.memory, current_instance, count, region, req.simulation_hours)

    # Apply changes
    sim_instance = current_instance
    sim_count = count
    sim_region = region

    for change in req.changes:
        if change.action == "resize" and change.instance_type_to:
            sim_instance = change.instance_type_to
            if change.instance_type_to not in _INSTANCE_KWH:
                warnings.append(f"Instance type '{change.instance_type_to}' not in demo catalog — using m5.large")
                sim_instance = "m5.large"
        elif change.action == "scale_out":
            sim_count = int(count * change.scale_factor)
            sim_count = max(1, min(20, sim_count))
        elif change.action == "scale_in":
            sim_count = max(1, int(count / change.scale_factor))
        elif change.action == "migrate" and change.target_region:
            sim_region = change.target_region
        elif change.action == "consolidate":
            sim_count = max(1, count // 2)
        elif change.action == "terminate":
            sim_count = 0
            warnings.append("Terminate action simulated — all instances removed")

    # After state
    if sim_count == 0:
        after = SimulationMetrics(
            cpu=0, memory=0 if m.memory is not None else None, cost_usd_per_hour=0, carbon_gco2_per_hour=0,
            monthly_cost_usd=0, monthly_carbon_kgco2=0,
            source="SIMULATED",
        )
    else:
        # Estimate cpu/memory shift from resize
        cpu_factor = _INSTANCE_KWH.get(sim_instance, 0.35) / _INSTANCE_KWH.get(current_instance, 0.35)
        new_cpu = round(min(98, m.cpu / cpu_factor), 1)
        new_mem = round(min(95, m.memory * 0.9), 1) if m.memory is not None else None
        after = _compute_metrics(new_cpu, new_mem, sim_instance, sim_count, sim_region, req.simulation_hours)

    def pct(a, b):
        if a == 0:
            return 0.0
        return round((b - a) / a * 100, 1)

    delta = {
        "cost_pct": pct(before.cost_usd_per_hour, after.cost_usd_per_hour),
        "carbon_pct": pct(before.carbon_gco2_per_hour, after.carbon_gco2_per_hour),
        "monthly_cost_pct": pct(before.monthly_cost_usd, after.monthly_cost_usd),
        "monthly_carbon_pct": pct(before.monthly_carbon_kgco2, after.monthly_carbon_kgco2),
        "p95_latency_pct": pct(before.p95_latency_ms, after.p95_latency_ms),
        "risk_score_delta": round(after.risk_score - before.risk_score, 1),
    }

    parts = []
    if delta["monthly_cost_pct"] < -5:
        parts.append(f"Saves ${before.monthly_cost_usd - after.monthly_cost_usd:.0f}/month ({abs(delta['monthly_cost_pct']):.0f}% cost reduction).")
    elif delta["monthly_cost_pct"] > 5:
        parts.append(f"Costs ${after.monthly_cost_usd - before.monthly_cost_usd:.0f}/month more ({delta['monthly_cost_pct']:.0f}% increase).")
    if delta["monthly_carbon_pct"] < -5:
        parts.append(f"Reduces emissions by {abs(delta['monthly_carbon_pct']):.0f}%.")
    if delta["p95_latency_pct"] < -5:
        parts.append(f"Improves P95 latency by {abs(delta['p95_latency_pct']):.0f}%.")
    elif delta["p95_latency_pct"] > 10:
        parts.append(f"Increases P95 latency by {delta['p95_latency_pct']:.0f}%.")
    if delta["risk_score_delta"] < 0:
        parts.append(f"Lowers operational risk by {abs(delta['risk_score_delta']):.1f} pts.")
    elif delta["risk_score_delta"] > 5:
        parts.append(f"Warning: Increases risk by {delta['risk_score_delta']:.1f} pts.")
    if not parts:
        parts.append("Minimal impact on cost and carbon — change is neutral.")

    confidence = 0.82 if len(req.changes) == 1 else 0.72
    sim_id = str(uuid.uuid4())[:8]
    rec_text = " ".join(parts)

    # Persist simulation to database asynchronously
    try:
        import asyncio
        from ..database import persist_simulation_entry
        coro = persist_simulation_entry(
            sim_id=sim_id,
            changes={"changes": [c.model_dump() for c in req.changes]},
            before=before.model_dump(),
            after=after.model_dump(),
            delta=delta,
            risk_score=0.15 if delta["monthly_cost_pct"] <= 0 else 0.40,
            recommendation=rec_text,
            confidence=confidence,
        )
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            try:
                asyncio.run(coro)
            except RuntimeError:
                pass
    except Exception:
        pass

    return SimulationResult(
        simulation_id=sim_id,
        before=before,
        after=after,
        delta=delta,
        recommendation=rec_text,
        confidence=confidence,
        warnings=warnings,
        source="SIMULATED",
        baseline_source=m.source,
    )


@router.post("/scenario", response_model=ScenarioSimulationResult)
def simulate_scenario(req: SimulationScenarioRequest):
    """Run a high-level scenario simulation (RIGHT_SIZE, SCALE_UP, SCALE_DOWN, CONSOLIDATE)."""
    from ..digital_twin import simulator as dt_simulator
    return dt_simulator.run_simulation(req)
