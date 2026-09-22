"""
Performance Agent — detects CPU/memory bottlenecks, SLO risks,
and scaling opportunities.
"""

from __future__ import annotations

from datetime import datetime

from ..schemas import CloudMetrics, RecommendationItem


def analyze(metrics: CloudMetrics, context: dict | None = None) -> dict:
    findings: list[str] = []
    recs: list[RecommendationItem] = []
    score = 100

    cpu = metrics.cpu
    memory = metrics.memory
    network = metrics.network

    # ── CPU saturation ────────────────────────────────────────────────────────
    if cpu > 90:
        score -= 35
        findings.append(f"CPU CRITICAL: {cpu:.0f}% — risk of request throttling")
        recs.append(RecommendationItem(
            id="perf-001",
            category="performance",
            priority="critical",
            title="Immediate CPU scale-out required",
            description=f"CPU is at {cpu:.0f}% — above 90% threshold. "
                        "Latency-sensitive workloads are likely experiencing degraded response times.",
            impact_summary="Imminent SLO breach — scale-out within 5 minutes",
            estimated_monthly_savings_usd=0,
            effort="low",
            action="emergency_scale_out",
            evidence=[f"Current CPU: {cpu:.1f}%", "Threshold: 90%"],
            confidence=0.97,
        ))
    elif cpu > 75:
        score -= 20
        findings.append(f"CPU elevated: {cpu:.0f}% — approaching saturation")
        recs.append(RecommendationItem(
            id="perf-002",
            category="performance",
            priority="high",
            title="Proactive CPU scale-out recommended",
            description=f"CPU at {cpu:.0f}% is trending toward the 90% alert threshold. "
                        "Adding capacity now prevents latency spikes.",
            impact_summary="Prevent SLO breach — scale proactively",
            estimated_monthly_savings_usd=0,
            effort="low",
            action="proactive_scale_out",
            evidence=[f"CPU: {cpu:.1f}%", "Rising trend detected"],
            confidence=0.88,
        ))

    # ── Memory pressure ───────────────────────────────────────────────────────
    if memory > 88:
        score -= 30
        findings.append(f"Memory CRITICAL: {memory:.0f}% — OOM risk")
        recs.append(RecommendationItem(
            id="perf-003",
            category="performance",
            priority="critical",
            title="Memory pressure critical — risk of OOM kill",
            description=f"Memory utilization is {memory:.0f}%. Above 88%, the OS kernel may "
                        "begin killing processes to free memory.",
            impact_summary="OOM kill risk — upgrade instance memory tier immediately",
            estimated_monthly_savings_usd=0,
            effort="medium",
            action="upgrade_memory_tier",
            evidence=[f"Memory: {memory:.1f}%", "OOM threshold: 88%"],
            confidence=0.95,
        ))
    elif memory > 75:
        score -= 15
        findings.append(f"Memory elevated: {memory:.0f}%")
        recs.append(RecommendationItem(
            id="perf-004",
            category="performance",
            priority="medium",
            title="Memory utilization trending high",
            description=f"Memory at {memory:.0f}% — investigate memory leaks or plan upgrade.",
            impact_summary="Prevent OOM events — investigate and right-size",
            estimated_monthly_savings_usd=0,
            effort="medium",
            action="investigate_memory",
            evidence=[f"Memory: {memory:.1f}%"],
            confidence=0.82,
        ))

    # ── Network saturation ────────────────────────────────────────────────────
    if network > 1500:
        score -= 15
        findings.append(f"Network throughput high: {network:.0f} Mbps")
        recs.append(RecommendationItem(
            id="perf-005",
            category="performance",
            priority="medium",
            title="Network throughput approaching instance limits",
            description=f"Network at {network:.0f} Mbps — consider enhanced networking or CDN offload.",
            impact_summary="Reduce latency with CDN offload or network-optimized instances",
            estimated_monthly_savings_usd=0,
            effort="high",
            action="enable_enhanced_networking",
            evidence=[f"Network: {network:.0f} Mbps"],
            confidence=0.78,
        ))

    # ── Healthy state ─────────────────────────────────────────────────────────
    if not findings:
        findings.append(f"All performance metrics nominal: CPU {cpu:.0f}%, Memory {memory:.0f}%")

    return {
        "agent": "PerformanceAgent",
        "status": "completed",
        "findings": findings,
        "recommendations": recs,
        "score": max(0, min(100, score)),
        "analyzed_at": datetime.utcnow().isoformat(),
    }
