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

    ctx = context or {}
    instance_count = metrics.instance_count
    cpu = metrics.cpu

    # ── Single point of failure ───────────────────────────────────────────────
    az_count = ctx.get("availability_zones", 1)
    if instance_count == 1 or az_count == 1:
        score -= 30
        findings.append(f"Single instance / single AZ — no redundancy")
        recs.append(RecommendationItem(
            id="rel-001",
            category="reliability",
            priority="high",
            title="Deploy across multiple Availability Zones",
            description="Running in a single AZ with a single instance creates a hard single point of failure. "
                        "Any AZ outage causes complete downtime. Deploy in at least 2 AZs with a load balancer.",
            impact_summary="Eliminate SPOF — target 99.9%+ SLA",
            estimated_monthly_savings_usd=0,
            effort="high",
            action="multi_az_deployment",
            evidence=[
                f"Instance count: {instance_count}",
                f"Availability zones: {az_count}",
            ],
            confidence=0.95,
        ))

    # ── No auto-scaling policy ────────────────────────────────────────────────
    has_autoscaling = ctx.get("has_autoscaling", False)
    if not has_autoscaling and cpu > 50:
        score -= 20
        findings.append("No auto-scaling policy configured — manual scaling only")
        recs.append(RecommendationItem(
            id="rel-002",
            category="reliability",
            priority="high",
            title="Configure auto-scaling policies",
            description="Without auto-scaling, sudden traffic spikes will cause CPU saturation and service degradation. "
                        "Configure target-tracking policies based on CPU and request rate.",
            impact_summary="Prevent SLO breach during traffic spikes",
            estimated_monthly_savings_usd=0,
            effort="medium",
            action="configure_autoscaling",
            evidence=[f"Current CPU: {cpu:.0f}%", "No ASG policy detected"],
            confidence=0.88,
        ))

    # ── Backup policy ─────────────────────────────────────────────────────────
    has_backups = ctx.get("has_backup_policy", False)
    backup_age_hours = ctx.get("last_backup_age_hours", 48)
    if not has_backups or backup_age_hours > 24:
        score -= 20
        findings.append(f"Last backup: {backup_age_hours}h ago — exceeds RPO target")
        recs.append(RecommendationItem(
            id="rel-003",
            category="reliability",
            priority="medium",
            title="Configure automated backups with RPO < 24h",
            description=f"Last backup was {backup_age_hours}h ago, exceeding typical 24h RPO targets. "
                        "Enable automated daily snapshots and test restore procedures.",
            impact_summary="Reduce recovery point objective — meet RPO SLA",
            estimated_monthly_savings_usd=0,
            effort="low",
            action="configure_automated_backups",
            evidence=[f"Last backup: {backup_age_hours}h ago"],
            confidence=0.90,
        ))

    # ── Health checks ─────────────────────────────────────────────────────────
    has_health_checks = ctx.get("has_health_checks", True)
    if not has_health_checks:
        score -= 15
        findings.append("No load balancer health checks configured")
        recs.append(RecommendationItem(
            id="rel-004",
            category="reliability",
            priority="medium",
            title="Enable load balancer health checks",
            description="Without health checks, traffic continues to route to unhealthy instances. "
                        "Configure HTTP health checks on your service endpoint.",
            impact_summary="Prevent routing to unhealthy instances",
            estimated_monthly_savings_usd=0,
            effort="low",
            action="configure_health_checks",
            evidence=["No health check endpoint configured"],
            confidence=0.85,
        ))

    # ── Healthy reliability ───────────────────────────────────────────────────
    if not recs:
        findings.append("Reliability configuration looks healthy")

    return {
        "agent": "ReliabilityAgent",
        "status": "completed",
        "findings": findings,
        "recommendations": recs,
        "score": max(0, min(100, score)),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }
