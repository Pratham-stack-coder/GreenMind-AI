"""
Reliability Agent — evaluates only observed instance counts and supplied topology,
backup, scaling, and health-check context.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..schemas import CloudMetrics, RecommendationItem


def analyze(metrics: CloudMetrics, context: dict | None = None) -> dict:
    findings: list[str] = []
    recs: list[RecommendationItem] = []
    score = 100
    ctx = context if isinstance(context, dict) else {}
    valid_posture: set[str] = set()

    availability_zones = ctx.get("availability_zones")
    if isinstance(availability_zones, int) and not isinstance(availability_zones, bool) and availability_zones >= 0:
        valid_posture.add("availability_zones")
    has_autoscaling = ctx.get("has_autoscaling")
    if isinstance(has_autoscaling, bool):
        valid_posture.add("has_autoscaling")
    has_backup_policy = ctx.get("has_backup_policy")
    if isinstance(has_backup_policy, bool):
        valid_posture.add("has_backup_policy")
    has_health_checks = ctx.get("has_health_checks")
    if isinstance(has_health_checks, bool):
        valid_posture.add("has_health_checks")
    raw_backup_age = ctx.get("last_backup_age_hours")
    backup_age = (
        float(raw_backup_age)
        if isinstance(raw_backup_age, (int, float)) and not isinstance(raw_backup_age, bool) and raw_backup_age >= 0
        else None
    )
    if backup_age is not None:
        valid_posture.add("last_backup_age_hours")

    instance_count_observed = (
        "instance_count" in getattr(metrics, "model_fields_set", set())
        and str(metrics.source).startswith("LIVE")
    )
    instance_count = metrics.instance_count
    cpu = metrics.cpu

    if (instance_count_observed and instance_count == 1) or availability_zones == 1:
        evidence = []
        if instance_count_observed:
            evidence.append(f"Instance count observed: {instance_count} ({metrics.source})")
        if availability_zones is not None:
            evidence.append(f"Availability zones supplied: {availability_zones}")
        else:
            evidence.append("Availability-zone placement was not provided")
        findings.append("Single-instance or single-zone deployment needs redundancy review")
        recs.append(RecommendationItem(
            id="rel-001",
            category="reliability",
            priority="high",
            title="Review availability-zone redundancy",
            description=(
                "The selected scope reports one instance or one availability zone. "
                "Verify the workload's failover requirements and deploy across multiple zones if needed."
            ),
            impact_summary="Reduce single-point-of-failure risk after topology is verified",
            estimated_monthly_savings_usd=0,
            effort="high",
            action="multi_az_deployment",
            evidence=evidence,
            confidence=0.75 if "availability_zones" not in ctx else 0.9,
        ))
        score -= 30

    if has_autoscaling is False and cpu > 50:
        findings.append("No auto-scaling policy was supplied for a workload above 50% CPU")
        recs.append(RecommendationItem(
            id="rel-002",
            category="reliability",
            priority="high",
            title="Review auto-scaling policies",
            description=(
                "The supplied configuration reports no auto-scaling policy while CPU is elevated. "
                "Validate scaling requirements and configure target tracking if appropriate."
            ),
            impact_summary="Improve response to traffic spikes after scaling requirements are verified",
            estimated_monthly_savings_usd=0,
            effort="medium",
            action="configure_autoscaling",
            evidence=[f"Current CPU: {cpu:.0f}%", "No auto-scaling policy in supplied context"],
            confidence=0.85,
        ))
        score -= 20

    backup_policy_missing = has_backup_policy is False
    backup_is_stale = backup_age is not None and backup_age > 24
    if backup_policy_missing or backup_is_stale:
        findings.append("Supplied backup configuration is missing or exceeds the 24-hour review target")
        evidence = []
        if backup_policy_missing:
            evidence.append("No backup policy in supplied context")
        if backup_age is not None:
            evidence.append(f"Last backup: {backup_age}h ago")
        recs.append(RecommendationItem(
            id="rel-003",
            category="reliability",
            priority="medium",
            title="Review automated backup coverage and recovery objectives",
            description=(
                "The supplied backup information indicates missing coverage or an old snapshot. "
                "Confirm the required recovery point objective and test restore procedures."
            ),
            impact_summary="Improve recoverability after backup coverage is verified",
            estimated_monthly_savings_usd=0,
            effort="low",
            action="configure_automated_backups",
            evidence=evidence,
            confidence=0.85,
        ))
        score -= 20

    if has_health_checks is False:
        findings.append("The supplied configuration reports no load-balancer health checks")
        recs.append(RecommendationItem(
            id="rel-004",
            category="reliability",
            priority="medium",
            title="Review load-balancer health checks",
            description=(
                "The supplied configuration reports no health checks. Verify routing behavior "
                "and configure probes if the service uses a load balancer."
            ),
            impact_summary="Reduce the chance of routing traffic to unhealthy instances",
            estimated_monthly_savings_usd=0,
            effort="low",
            action="configure_health_checks",
            evidence=["No health checks in supplied context"],
            confidence=0.8,
        ))
        score -= 15

    if not findings and not valid_posture:
        findings.append(
            "Reliability posture data is unavailable; topology, backup, scaling, and health checks were not inferred."
        )
        status = "skipped"
    elif not findings:
        findings.append(
            "No issues were found in supplied reliability checks; unprovided checks remain unverified."
        )
        status = "completed"
    else:
        status = "completed"

    return {
        "agent": "ReliabilityAgent",
        "status": status,
        "findings": findings,
        "recommendations": recs,
        "score": max(0, min(100, score)),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }
