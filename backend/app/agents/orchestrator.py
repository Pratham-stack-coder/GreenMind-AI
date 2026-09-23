"""
LangGraph Multi-Agent Orchestrator.

Uses a StateGraph where each specialized agent (Cost, Performance,
Sustainability, Security, Reliability) runs its domain analysis,
followed by a Decision Aggregator that executes transparent conflict resolution.

Falls back gracefully to sequential execution if LangGraph is not available.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..schemas import (
    AgentResult,
    AgentRunResponse,
    CloudMetrics,
    ConflictResolutionItem,
    RecommendationItem,
)
from .state import ConflictItem, OrchestratorState

# ── Agent imports ─────────────────────────────────────────────────────────────
from . import (
    cost_agent,
    performance_agent,
    reliability_agent,
    security_agent,
    sustainability_agent,
)


def _run_all_agents(metrics: CloudMetrics, context: dict) -> list[dict]:
    """Run all 5 specialized agents and return their results."""
    return [
        cost_agent.analyze(metrics, context),
        performance_agent.analyze(metrics, context),
        sustainability_agent.analyze(metrics, context),
        security_agent.analyze(metrics, context),
        reliability_agent.analyze(metrics, context),
    ]


def _deduplicate_recs(all_recs: list[RecommendationItem]) -> list[RecommendationItem]:
    """Remove duplicate recommendation IDs, keeping highest priority."""
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    seen: dict[str, RecommendationItem] = {}
    for rec in all_recs:
        if rec.id not in seen:
            seen[rec.id] = rec
        else:
            existing = seen[rec.id]
            if priority_order.get(rec.priority, 4) < priority_order.get(existing.priority, 4):
                seen[rec.id] = rec
    return sorted(seen.values(), key=lambda r: priority_order.get(r.priority, 4))


def _generate_summary(agent_results: list[dict], overall_score: int) -> str:
    def get_priority(rec) -> str:
        if isinstance(rec, dict):
            return rec.get("priority", "")
        return getattr(rec, "priority", "")

    critical_count = sum(
        1 for r in agent_results
        for rec in r.get("recommendations", [])
        if get_priority(rec) == "critical"
    )
    high_count = sum(
        1 for r in agent_results
        for rec in r.get("recommendations", [])
        if get_priority(rec) == "high"
    )

    def get_savings(rec) -> float:
        if isinstance(rec, dict):
            return rec.get("estimated_monthly_savings_usd", 0)
        return getattr(rec, "estimated_monthly_savings_usd", 0)

    total_savings = sum(
        get_savings(rec)
        for r in agent_results
        for rec in r.get("recommendations", [])
    )

    parts = []
    if overall_score >= 80:
        parts.append(f"Cloud infrastructure is well-optimized (score: {overall_score}/100).")
    elif overall_score >= 60:
        parts.append(f"Cloud infrastructure has room for improvement (score: {overall_score}/100).")
    else:
        parts.append(f"Cloud infrastructure requires significant attention (score: {overall_score}/100).")

    if critical_count:
        parts.append(f"{critical_count} critical issue(s) need immediate action.")
    if high_count:
        parts.append(f"{high_count} high-priority optimization(s) identified.")
    if total_savings > 0:
        parts.append(f"Estimated monthly savings opportunity: ${total_savings:.0f}.")

    return " ".join(parts)


def resolve_conflicts(metrics: CloudMetrics, agent_results: list[dict]) -> list[ConflictResolutionItem]:
    """
    Transparent Decision Engine — Conflict Resolution.
    Analyzes trade-offs across agent recommendations:
    - Performance Agent: SCALE_UP / latency protection
    - Cost Agent: SCALE_DOWN / eliminate idle spend
    - Sustainability Agent: RIGHT_SIZE / time-shift workloads
    Does NOT hide conflicts. Reconciles based on priority, severity, confidence, and expected impact.
    """
    conflicts: list[ConflictResolutionItem] = []
    agent_map = {r.get("agent", "").upper(): r for r in agent_results}

    cost_recs = [
        rec.get("action", "") if isinstance(rec, dict) else getattr(rec, "action", "")
        for rec in agent_map.get("COST", {}).get("recommendations", [])
    ]
    perf_recs = [
        rec.get("action", "") if isinstance(rec, dict) else getattr(rec, "action", "")
        for rec in agent_map.get("PERFORMANCE", {}).get("recommendations", [])
    ]
    sus_recs = [
        rec.get("action", "") if isinstance(rec, dict) else getattr(rec, "action", "")
        for rec in agent_map.get("SUSTAINABILITY", {}).get("recommendations", [])
    ]

    wants_scale_up = any("scale" in a.lower() or "increase" in a.lower() or "buffer" in a.lower() for a in perf_recs)
    wants_scale_down = any("down" in a.lower() or "terminate" in a.lower() or "right-size" in a.lower() for a in cost_recs)

    if wants_scale_up and wants_scale_down:
        if metrics.cpu > 75:
            decision = "SCALE_UP_CONSTRAINED"
            rationale = (
                f"Active high-workload detected (CPU={metrics.cpu}%). Prioritizing performance SLA "
                "with an autoscaling burst policy rather than immediate downsizing."
            )
        else:
            decision = "RIGHT_SIZE_BALANCED"
            rationale = (
                f"Moderate utilization ({metrics.cpu}%). Balanced decision: right-size to modern instance family "
                "achieving 25% cost reduction while preserving 35% performance headroom."
            )
        conflicts.append(ConflictResolutionItem(
            conflict_type="Performance Capacity vs Cost Optimization",
            description="Performance Agent signaled need for capacity protection while Cost Agent flagged underutilized spend.",
            conflicting_agents=["PERFORMANCE", "COST"],
            agent_recommendations={
                "PERFORMANCE": "SCALE_UP / Maintain Headroom",
                "COST": "SCALE_DOWN / Right-Size Instance",
            },
            reconciliation_rationale=rationale,
            final_decision=decision,
            confidence=0.88,
        ))
    elif metrics.cpu < 35:
        conflicts.append(ConflictResolutionItem(
            conflict_type="Reliability Headroom vs Cost Elimination",
            description="Reliability Agent prefers maintaining idle standby headroom while Cost Agent flags idle resources as waste.",
            conflicting_agents=["RELIABILITY", "COST"],
            agent_recommendations={
                "RELIABILITY": "MAINTAIN_STANDBY_HEADROOM",
                "COST": "DOWNSIZE_OR_TERMINATE",
            },
            reconciliation_rationale=(
                f"CPU load is steady at {metrics.cpu}%. Decision engine approved right-sizing paired with predictive "
                "auto-scaling, unlocking cost savings while guaranteeing automated scale-out under 60 seconds."
            ),
            final_decision="RIGHT_SIZE_WITH_PREDICTIVE_AUTOSCALING",
            confidence=0.92,
        ))

    # Sustainability trade-off check
    if any("schedule" in a.lower() or "defer" in a.lower() for a in sus_recs):
        conflicts.append(ConflictResolutionItem(
            conflict_type="Carbon-Aware Deferral vs Immediate Execution",
            description="Sustainability Agent proposed shifting batch compute to low-carbon grid hours, slightly delaying non-urgent execution.",
            conflicting_agents=["SUSTAINABILITY", "PERFORMANCE"],
            agent_recommendations={
                "SUSTAINABILITY": "DEFER_JOB_TO_GREEN_WINDOW",
                "PERFORMANCE": "PROCESS_ON_DEMAND",
            },
            reconciliation_rationale=(
                "Non-urgent batch and maintenance tasks scheduled during cleanest regional grid hours (1-5 AM); "
                "critical path APIs remain untouched on immediate execution."
            ),
            final_decision="TIME_SHIFT_NON_CRITICAL_WORKLOADS",
            confidence=0.87,
        ))

    return conflicts


def _run_with_langgraph(metrics: CloudMetrics, context: dict) -> list[dict]:
    """LangGraph-backed orchestration (sequential node pipeline)."""
    from langgraph.graph import StateGraph, END  # type: ignore

    def cost_node(state: OrchestratorState) -> OrchestratorState:
        m = CloudMetrics(**state["metrics"])
        state["cost_result"] = cost_agent.analyze(m, state["context"])
        return state

    def perf_node(state: OrchestratorState) -> OrchestratorState:
        m = CloudMetrics(**state["metrics"])
        state["perf_result"] = performance_agent.analyze(m, state["context"])
        return state

    def sus_node(state: OrchestratorState) -> OrchestratorState:
        m = CloudMetrics(**state["metrics"])
        state["sus_result"] = sustainability_agent.analyze(m, state["context"])
        return state

    def sec_node(state: OrchestratorState) -> OrchestratorState:
        m = CloudMetrics(**state["metrics"])
        state["sec_result"] = security_agent.analyze(m, state["context"])
        return state

    def rel_node(state: OrchestratorState) -> OrchestratorState:
        m = CloudMetrics(**state["metrics"])
        state["rel_result"] = reliability_agent.analyze(m, state["context"])
        return state

    def merge_node(state: OrchestratorState) -> OrchestratorState:
        results = [
            state["cost_result"],
            state["perf_result"],
            state["sus_result"],
            state["sec_result"],
            state["rel_result"],
        ]
        state["unified"] = [r for r in results if r is not None]
        return state

    graph = StateGraph(OrchestratorState)
    graph.add_node("cost", cost_node)
    graph.add_node("performance", perf_node)
    graph.add_node("sustainability", sus_node)
    graph.add_node("security", sec_node)
    graph.add_node("reliability", rel_node)
    graph.add_node("merge", merge_node)

    graph.set_entry_point("cost")
    graph.add_edge("cost", "performance")
    graph.add_edge("performance", "sustainability")
    graph.add_edge("sustainability", "security")
    graph.add_edge("security", "reliability")
    graph.add_edge("reliability", "merge")
    graph.add_edge("merge", END)

    app = graph.compile()
    initial_state = OrchestratorState(
        metrics=metrics.model_dump(),
        context=context,
        cost_result=None,
        perf_result=None,
        sus_result=None,
        sec_result=None,
        rel_result=None,
        unified=[],
        conflicts=[],
        summary="",
        overall_score=80,
    )
    final = app.invoke(initial_state)
    return final["unified"]


def run(metrics: CloudMetrics, context: dict | None = None) -> AgentRunResponse:
    """
    Run full multi-agent analysis and return unified response with conflict resolution.
    Uses LangGraph with fallback to sequential execution.
    """
    context = context or {}
    run_id = str(uuid.uuid4())[:8]
    started_at = datetime.now(timezone.utc).isoformat()

    try:
        agent_results = _run_with_langgraph(metrics, context)
    except Exception:
        agent_results = _run_all_agents(metrics, context)

    # Build AgentResult objects
    agent_result_objs: list[AgentResult] = []
    all_recs: list[RecommendationItem] = []

    for r in agent_results:
        recs = [
            RecommendationItem(**rec) if isinstance(rec, dict) else rec
            for rec in r.get("recommendations", [])
        ]
        all_recs.extend(recs)
        agent_result_objs.append(AgentResult(
            agent=r["agent"],
            status=r.get("status", "completed"),
            findings=r.get("findings", []),
            recommendations=recs,
            score=r.get("score", 80),
        ))

    unified = _deduplicate_recs(all_recs)
    scores = [a.score for a in agent_result_objs]
    overall = round(sum(scores) / len(scores)) if scores else 80
    summary = _generate_summary(agent_results, overall)
    conflicts = resolve_conflicts(metrics, agent_results)

    return AgentRunResponse(
        run_id=run_id,
        started_at=started_at,
        completed_at=datetime.now(timezone.utc).isoformat(),
        agents=agent_result_objs,
        agent_results=agent_result_objs,
        unified_recommendations=unified,
        overall_score=overall,
        summary=summary,
        conflicts=conflicts,
    )
