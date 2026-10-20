"""
Reliability Agent — detects single points of failure, backup gaps,
availability zone distribution issues, and health check misconfigurations.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..schemas import CloudMetrics, RecommendationItem


def analyze(metrics: CloudMetrics, context: dict | None = None) -> dict:
    findings: list[str] = []
    recs: list[RecommendationItem] = []
    score = 100

    ctx = context if isinstance(context, dict) else {}
    cpu = metrics.cpu

    # Evaluate posture signals only when caller supplied them
    availability_zones = ctx.get("availability_zones")
    has_autoscaling = ctx.get("has_autoscaling")
    has_backup_policy = ctx.get("has_backup_policy")
    backup_age = ctx.get("last_backup_age_hours")
    has_health_checks = ctx.get("has_health_checks")

    valid_posture = any(
        val is not None
        for val in (availability_zones, has_autoscaling, has_backup_policy, backup_age, has_health_checks)
    )

    if not valid_posture:
        return {
            "agent": "ReliabilityAgent",
            "status": "skipped",
            "findings": [
                "Reliability posture data is unavailable; topology, backup, scaling, and health checks were not inferred."
            ],
            "recommendations": [],
            "score": 100,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    # ── Single point of failure / Topology ────────────────────────────────────
    single_instance = metrics.instance_count is not None and metrics.instance_count == 1
    single_az = isinstance(availability_zones, int) and availability_zones == 1
    if single_instance or single_az:
        evidence = []
        if metrics.instance_count is not None:
            evidence.append(f"Instance count: {metrics.instance_count}")
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

    # ── No auto-scaling policy ────────────────────────────────────────────────
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

    # ── Backup policy ─────────────────────────────────────────────────────────
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

    # ── Health checks ─────────────────────────────────────────────────────────
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

    # ── Completion status ─────────────────────────────────────────────────────
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
