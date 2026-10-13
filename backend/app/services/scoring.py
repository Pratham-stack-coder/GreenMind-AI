"""
Unified Optimization Scoring Engine for GreenMind AI.

Single documented source of truth for computing 5-pillar cloud optimization
scores across:
1. Cost Optimization (0–100)
2. Performance & Capacity Headroom (0–100)
3. Sustainability & Carbon Efficiency (0–100)
4. Security Posture (0–100, explicitly marked as ESTIMATED until live scanner integration)
5. Reliability & HA Architecture (0–100, explicitly marked as ESTIMATED until multi-AZ telemetry)

Methodology & Invariants:
- Evaluates both baseline telemetry and simulated after-state metrics deterministically.
- All domain scores and composite scores are strictly bounded between [0, 100].
- Missing metrics (e.g., guest OS memory when CWAgent is absent, unconfigured scanners)
  are handled explicitly via `val if val is not None else fallback` and documented in `assumptions`.
- Valid zero values (e.g., cpu=0.0 on a hibernated or idle instance) are preserved and NOT
  misclassified as missing metrics.
- Output source clearly reports DEMO, ESTIMATED, LIVE, or SIMULATED.
- No arbitrary artificial score boosts are used; score changes strictly reflect metric movements.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel

from .. import carbon
from ..schemas import CloudMetrics, DataSourceType, OptimizationScores


# ── Domain-Specific Scoring Calculations ─────────────────────────────────────

def compute_cost_score(
    cpu: float | None,
    memory: float | None = None,
    cost_usd_per_hour: float | None = None,
    instance_count: int = 1,
) -> tuple[int, list[str]]:
    """
    Calculate Cost Optimization score (0–100).
    Ideal operational CPU utilization band: 30% <= cpu <= 75%.
    - Underutilization (<30% or <15%) indicates overprovisioning or idle burn.
    - Extreme underutilization (<10%) incurs heavy idle waste penalties.
    - Mild overutilization (>85%) incurs a minor cost-efficiency penalty due to delayed scaling.
    - Zero readings (cpu=0.0) are treated as completely idle instances, NOT missing data.
    """
    assumptions: list[str] = []
    if cpu is None:
        assumptions.append("CPU utilization unavailable; assumed baseline 50.0% for cost evaluation.")
        eff_cpu = 50.0
    else:
        eff_cpu = float(cpu)

    # Base cost score begins at optimal 100
    penalty = 0

    if eff_cpu < 10.0:
        penalty += 50  # Severely idle instance
        assumptions.append("Instance CPU < 10%: heavy idle waste penalty (-50 pts).")
    elif eff_cpu < 25.0:
        penalty += 25  # Underutilized
        assumptions.append("Instance CPU < 25%: overprovisioning penalty (-25 pts).")
    elif eff_cpu > 85.0:
        penalty += 15  # Inefficient over-saturation
        assumptions.append("Instance CPU > 85%: saturation stress penalty (-15 pts).")

    if memory is not None:
        eff_mem = float(memory)
        if eff_mem < 20.0 and eff_cpu < 20.0:
            penalty += 15  # Idle memory headroom
            assumptions.append("Low memory utilization (<20%) confirms idle compute allocation.")
        elif eff_mem > 85.0:
            penalty += 10
    else:
        assumptions.append("Guest OS memory telemetry unavailable (agent not installed); cost score relies on CPU.")

    score = max(0, min(100, 100 - penalty))
    return score, assumptions


def compute_performance_score(
    cpu: float | None,
    memory: float | None = None,
    network: float | None = None,
) -> tuple[int, list[str]]:
    """
    Calculate Performance & Capacity Headroom score (0–100).
    - CPU > 75% approaches saturation threshold (-20).
    - CPU > 90% risks immediate throttling / SLO breach (-35).
    - Memory > 80% indicates memory pressure (-15).
    - Memory > 90% presents severe OOM killer risk (-30).
    - Valid zero readings (e.g. cpu=0.0) represent maximum headroom (no saturation penalty).
    """
    assumptions: list[str] = []
    if cpu is None:
        assumptions.append("CPU telemetry unavailable; assuming 50.0% for performance baseline.")
        eff_cpu = 50.0
    else:
        eff_cpu = float(cpu)

    penalty = 0

    if eff_cpu > 90.0:
        penalty += 35
        assumptions.append("Critical CPU saturation (>90%): throttling risk (-35 pts).")
    elif eff_cpu > 75.0:
        penalty += 20
        assumptions.append("Elevated CPU utilization (>75%): queueing latency risk (-20 pts).")

    if memory is not None:
        eff_mem = float(memory)
        if eff_mem > 90.0:
            penalty += 30
            assumptions.append("Critical memory saturation (>90%): OOM killer risk (-30 pts).")
        elif eff_mem > 80.0:
            penalty += 15
            assumptions.append("High memory utilization (>80%): paging risk (-15 pts).")
    else:
        assumptions.append("Guest OS memory unavailable; performance evaluated on CPU and network.")

    if network is not None and network > 2000.0:
        penalty += 10
        assumptions.append("High network I/O (>2000 Mbps): interface saturation risk (-10 pts).")

    score = max(0, min(100, 100 - penalty))
    return score, assumptions


def compute_sustainability_score(
    carbon_intensity: float | None = None,
    region: str = "us-east",
    hour: int | None = None,
) -> tuple[int, list[str]]:
    """
    Calculate Sustainability score (0–100).
    Normalized against global regional grid boundaries:
    - Clean hydro/nuclear baseline: ~79 gCO2/kWh (100 score)
    - Fossil/coal-heavy grid ceiling: ~720 gCO2/kWh (0 score)
    """
    assumptions: list[str] = []
    if hour is None:
        hour = datetime.now(timezone.utc).hour

    if carbon_intensity is None:
        ci_data = carbon.get_carbon_intensity(region, hour)
        ci = float(ci_data.get("carbon_intensity_gco2_per_kwh", 350.0))
        assumptions.append(f"Grid carbon intensity derived from {region} hourly model: {ci:.0f} gCO2/kWh.")
    else:
        ci = float(carbon_intensity)

    # Normalize against grid envelope [79, 720]
    ci_clamped = max(79.0, min(720.0, ci))
    normalized = 100.0 - ((ci_clamped - 79.0) / (720.0 - 79.0) * 100.0)
    score = max(0, min(100, round(normalized)))
    return score, assumptions


def compute_security_score(
    findings_count: int | None = None,
    open_perimeter_ports: list[int] | None = None,
) -> tuple[int, list[str]]:
    """
    Calculate Security Posture score (0–100).
    Marked as ESTIMATED by default until live IAM / Security Hub / Defender integration.
    """
    assumptions: list[str] = [
        "Security score is an ESTIMATE pending live IAM / Security Hub / CSPM connection."
    ]
    base_score = 75

    if open_perimeter_ports:
        base_score -= len(open_perimeter_ports) * 15
        assumptions.append(f"Security group exposure: open ports {open_perimeter_ports} (-{len(open_perimeter_ports) * 15} pts).")

    if findings_count is not None and findings_count > 0:
        base_score -= findings_count * 10
        assumptions.append(f"Detected {findings_count} security posture findings.")

    score = max(0, min(100, base_score))
    return score, assumptions


def compute_reliability_score(
    instance_count: int = 1,
    multi_az: bool | None = None,
) -> tuple[int, list[str]]:
    """
    Calculate Reliability score (0–100).
    Marked as ESTIMATED by default until multi-AZ and health check telemetry are connected.
    """
    assumptions: list[str] = [
        "Reliability score is an ESTIMATE pending multi-AZ and health-check agent telemetry."
    ]
    if multi_az is True or instance_count >= 2:
        score = 80
        assumptions.append("Multi-node or multi-AZ deployment provides high availability.")
    else:
        score = 65
        assumptions.append("Single-instance deployment lacks HA redundancy (-15 pts).")

    return max(0, min(100, score)), assumptions


# ── Unified Scoring Function ──────────────────────────────────────────────────

def compute_optimization_scores(
    metrics: CloudMetrics | None = None,
    *,
    cpu: float | None = None,
    memory: float | None = None,
    network: float | None = None,
    cost_usd_per_hour: float | None = None,
    carbon_gco2_per_hour: float | None = None,
    carbon_intensity: float | None = None,
    region: str = "us-east",
    instance_count: int = 1,
    source: DataSourceType = "DEMO",
    findings_count: int | None = None,
    open_perimeter_ports: list[int] | None = None,
    multi_az: bool | None = None,
    is_simulated: bool = False,
    baseline_overall: int | None = None,
) -> OptimizationScores:
    """
    Single unified entrypoint for computing the 5-domain Optimization Score.
    Accepts either a CloudMetrics object or explicit keyword metrics.
    Ensures consistent scoring between:
    - /analytics/score
    - /recommendations
    - Digital Twin scenario simulations
    """
    if metrics is not None:
        eff_cpu = metrics.cpu
        eff_memory = metrics.memory
        eff_network = metrics.network
        eff_cost = metrics.cost_usd_per_hour
        eff_carbon = metrics.carbon_gco2_per_hour
        eff_ci = getattr(metrics, "carbon_intensity", None) or carbon_intensity
        eff_region = getattr(metrics, "region", None) or region
        eff_count = getattr(metrics, "instance_count", None) or instance_count
        eff_source: DataSourceType = "SIMULATED" if is_simulated else (getattr(metrics, "source", None) or source)
    else:
        eff_cpu = cpu
        eff_memory = memory
        eff_network = network
        eff_cost = cost_usd_per_hour
        eff_carbon = carbon_gco2_per_hour
        eff_ci = carbon_intensity
        eff_region = region
        eff_count = instance_count
        eff_source = "SIMULATED" if is_simulated else source

    all_assumptions: list[str] = []

    cost_score, cost_assumptions = compute_cost_score(
        cpu=eff_cpu,
        memory=eff_memory,
        cost_usd_per_hour=eff_cost,
        instance_count=eff_count,
    )
    all_assumptions.extend(cost_assumptions)

    perf_score, perf_assumptions = compute_performance_score(
        cpu=eff_cpu,
        memory=eff_memory,
        network=eff_network,
    )
    all_assumptions.extend(perf_assumptions)

    sus_score, sus_assumptions = compute_sustainability_score(
        carbon_intensity=eff_ci,
        region=eff_region,
    )
    all_assumptions.extend(sus_assumptions)

    sec_score, sec_assumptions = compute_security_score(
        findings_count=findings_count,
        open_perimeter_ports=open_perimeter_ports,
    )
    all_assumptions.extend(sec_assumptions)

    rel_score, rel_assumptions = compute_reliability_score(
        instance_count=eff_count,
        multi_az=multi_az,
    )
    all_assumptions.extend(rel_assumptions)

    overall = max(0, min(100, round((cost_score + perf_score + sus_score + sec_score + rel_score) / 5)))
    trend: Literal["improving", "stable", "declining"] = (
        "improving" if overall >= 70 else ("stable" if overall >= 50 else "declining")
    )

    score_delta = (overall - baseline_overall) if baseline_overall is not None else None

    return OptimizationScores(
        overall=overall,
        cost=cost_score,
        performance=perf_score,
        sustainability=sus_score,
        security=sec_score,
        reliability=rel_score,
        trend=trend,
        source=eff_source,
        is_simulated=is_simulated,
        baseline_overall=baseline_overall if is_simulated else overall,
        projected_overall=overall if is_simulated else None,
        score_delta=score_delta,
        assumptions=all_assumptions,
    )
