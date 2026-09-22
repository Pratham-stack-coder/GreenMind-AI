"""Digital Twin router — simulate infrastructure changes before applying."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter

from .. import carbon
from ..decision_engine import INSTANCE_COSTS
from ..schemas import SimulationMetrics, SimulationRequest, SimulationResult

router = APIRouter(prefix="/digital-twin", tags=["Digital Twin"])

_INSTANCE_KWH = {
    "t3.micro": 0.04, "t3.small": 0.08, "t3.medium": 0.15,
    "m5.large": 0.35, "m5.xlarge": 0.65, "m5.2xlarge": 1.2,
    "c5.large": 0.30, "c5.xlarge": 0.55,
    "r5.large": 0.40, "r5.xlarge": 0.75,
}


def _compute_metrics(
    cpu: float, memory: float, instance_type: str, count: int, region: str, hours: float
) -> SimulationMetrics:
    from datetime import datetime, timezone
    hour = datetime.now(timezone.utc).hour
    ci = carbon.get_carbon_intensity(region, hour)["carbon_intensity_gco2_per_kwh"]
    kwh = _INSTANCE_KWH.get(instance_type, 0.35)
    cost_hr = INSTANCE_COSTS.get(instance_type, 0.192) * count
    carbon_hr = round(kwh * ci * count, 2)
    monthly_cost = round(cost_hr * 24 * 30, 2)
    monthly_carbon_kg = round(carbon_hr * 24 * 30 / 1000, 3)
    return SimulationMetrics(
        cpu=cpu,
        memory=memory,
        cost_usd_per_hour=round(cost_hr, 4),
        carbon_gco2_per_hour=carbon_hr,
        monthly_cost_usd=monthly_cost,
        monthly_carbon_kgco2=monthly_carbon_kg,
    )


@router.post("/simulate", response_model=SimulationResult)
def simulate(req: SimulationRequest):
    """Simulate one or more infrastructure changes and return before/after impact."""
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
            cpu=0, memory=0, cost_usd_per_hour=0, carbon_gco2_per_hour=0,
            monthly_cost_usd=0, monthly_carbon_kgco2=0,
        )
    else:
        # Estimate cpu/memory shift from resize
        cpu_factor = _INSTANCE_KWH.get(sim_instance, 0.35) / _INSTANCE_KWH.get(current_instance, 0.35)
        new_cpu = round(min(98, m.cpu / cpu_factor), 1)
        new_mem = round(min(95, m.memory * 0.9), 1)  # resize generally improves headroom
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
    }

    parts = []
    if delta["monthly_cost_pct"] < -5:
        parts.append(f"Saves ${before.monthly_cost_usd - after.monthly_cost_usd:.0f}/month ({abs(delta['monthly_cost_pct']):.0f}% cost reduction).")
    elif delta["monthly_cost_pct"] > 5:
        parts.append(f"Costs ${after.monthly_cost_usd - before.monthly_cost_usd:.0f}/month more ({delta['monthly_cost_pct']:.0f}% increase).")
    if delta["monthly_carbon_pct"] < -5:
        parts.append(f"Reduces emissions by {abs(delta['monthly_carbon_pct']):.0f}%.")
    if not parts:
        parts.append("Minimal impact on cost and carbon — change may be beneficial for performance.")

    confidence = 0.82 if len(req.changes) == 1 else 0.72

    return SimulationResult(
        simulation_id=str(uuid.uuid4())[:8],
        before=before,
        after=after,
        delta=delta,
        recommendation=" ".join(parts),
        confidence=confidence,
        warnings=warnings,
    )
