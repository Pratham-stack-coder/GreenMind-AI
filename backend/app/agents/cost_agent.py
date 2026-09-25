"""
Cost Agent — detects overspend, idle resources, right-sizing opportunities,
and reserved-instance recommendations.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..schemas import CloudMetrics, RecommendationItem


def analyze(metrics: CloudMetrics, context: dict | None = None) -> dict:
    findings: list[str] = []
    recs: list[RecommendationItem] = []
    score = 100

    cpu = metrics.cpu
    memory = metrics.memory
    cost = metrics.cost_usd_per_hour
    instance_count = metrics.instance_count

    # ── Idle resource detection & Right-sizing ────────────────────────────────
    mem_str = f"{memory:.0f}%" if memory is not None else "UNAVAILABLE (Agent not installed)"
    mem_evidence = f"Current Memory: {mem_str}"

    if memory is not None:
        is_idle = cpu < 10 and memory < 25
        is_overprov = cpu < 25 and memory < 40 and instance_count == 1
    else:
        # Without guest OS agent memory, base sizing decisions cautiously on CPU alone
        is_idle = cpu < 10
        is_overprov = cpu < 25 and instance_count == 1
        findings.append("Guest OS memory telemetry is UNAVAILABLE — install CloudWatch/Azure Monitor agent for high-confidence sizing.")

    if is_idle:
        penalty = 30
        score -= penalty
        findings.append(f"Instance appears idle: CPU {cpu:.0f}%, Memory {mem_str}")
        recs.append(RecommendationItem(
            id="cost-001",
            category="cost",
            priority="high",
            title="Terminate or hibernate idle instances",
            description=f"CPU utilization is {cpu:.0f}% and memory is {mem_str}. "
                        "These instances are likely idle and incurring unnecessary cost.",
            impact_summary=f"~${cost * 24 * 30:.0f}/month wasted on idle compute",
            estimated_monthly_savings_usd=round(cost * 24 * 30 * 0.9, 2),
            effort="low",
            action="terminate_idle",
            evidence=[f"Current CPU: {cpu:.1f}%", mem_evidence],
            confidence=0.92 if memory is not None else 0.75,
        ))
    elif is_overprov:
        penalty = 20
        score -= penalty
        findings.append(f"Instance is over-provisioned: CPU {cpu:.0f}%, Memory {mem_str}")
        savings = round(cost * 0.4 * 24 * 30, 2)
        recs.append(RecommendationItem(
            id="cost-002",
            category="cost",
            priority="medium",
            title="Right-size to smaller instance type",
            description=f"Average CPU is {cpu:.0f}% and memory is {mem_str}. "
                        "Downsizing one tier could save ~40% of compute cost.",
            impact_summary=f"~${savings:.0f}/month savings from right-sizing",
            estimated_monthly_savings_usd=savings,
            effort="medium",
            action="right_size_down",
            evidence=[f"Current CPU avg: {cpu:.1f}%", mem_evidence],
            confidence=0.88 if memory is not None else 0.70,
        ))

    # ── Reserved instance opportunity ─────────────────────────────────────────
    if cost > 0.1:
        ri_savings = round(cost * 0.3 * 24 * 30, 2)
        score -= 10
        findings.append("Running on On-Demand pricing — Reserved Instances could save 30%+")
        recs.append(RecommendationItem(
            id="cost-003",
            category="cost",
            priority="medium",
            title="Purchase Reserved Instances (1-year term)",
            description="Sustained workloads on On-Demand pricing pay a premium. "
                        "A 1-year Reserved Instance typically saves 30-40%.",
            impact_summary=f"~${ri_savings:.0f}/month savings with 1yr RI",
            estimated_monthly_savings_usd=ri_savings,
            effort="low",
            action="purchase_reserved_instance",
            evidence=[f"Hourly On-Demand cost: ${cost:.4f}", "Workload appears sustained"],
            confidence=0.80,
        ))

    # ── Multi-instance consolidation ──────────────────────────────────────────
    if instance_count > 2 and cpu < 30:
        penalty = 15
        score -= penalty
        consolidate_count = max(1, instance_count // 2)
        findings.append(f"{instance_count} instances running at {cpu:.0f}% CPU — consolidation possible")
        recs.append(RecommendationItem(
            id="cost-004",
            category="cost",
            priority="high",
            title=f"Consolidate {instance_count} instances to {consolidate_count}",
            description=f"Running {instance_count} instances at low utilization is inefficient. "
                        f"Consolidating to {consolidate_count} instances can halve compute costs.",
            impact_summary=f"~${cost * (instance_count - consolidate_count) * 24 * 30:.0f}/month saved",
            estimated_monthly_savings_usd=round(cost * (instance_count - consolidate_count) * 24 * 30, 2),
            effort="medium",
            action="consolidate_instances",
            evidence=[f"Instance count: {instance_count}", f"Avg CPU: {cpu:.0f}%"],
            confidence=0.84,
        ))

    return {
        "agent": "CostAgent",
        "status": "completed",
        "findings": findings,
        "recommendations": recs,
        "score": max(0, min(100, score)),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }
