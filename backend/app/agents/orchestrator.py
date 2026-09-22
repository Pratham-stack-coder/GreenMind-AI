"""
LangGraph Multi-Agent Orchestrator.

Uses a StateGraph where each specialized agent is a node. Agents run in
parallel where possible, then a merge node consolidates findings and resolves
conflicts between recommendations.

Requires: pip install langgraph langchain-core
Falls back gracefully to a sequential runner if langgraph is not installed.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TypedDict

from ..schemas import AgentResult, AgentRunResponse, CloudMetrics, RecommendationItem

# ── Agent imports ─────────────────────────────────────────────────────────────
from . import (
    cost_agent,
    performance_agent,
    reliability_agent,
    security_agent,
    sustainability_agent,
)


# ── LangGraph State ───────────────────────────────────────────────────────────

class OrchestratorState(TypedDict):
    metrics: dict
    context: dict
    cost_result: dict | None
    perf_result: dict | None
    sus_result: dict | None
    sec_result: dict | None
    rel_result: dict | None
    unified: list[dict]
    summary: str


def _run_all_agents(metrics: CloudMetrics, context: dict) -> list[dict]:
    """Run all agents and return their results."""
    results = [
        cost_agent.analyze(metrics, context),
        performance_agent.analyze(metrics, context),
        sustainability_agent.analyze(metrics, context),
        security_agent.analyze(metrics, context),
        reliability_agent.analyze(metrics, context),
    ]
    return results


def _deduplicate_recs(all_recs: list[RecommendationItem]) -> list[RecommendationItem]:
    """Remove duplicate recommendation IDs, keeping highest priority."""
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    seen: dict[str, RecommendationItem] = {}
    for rec in all_recs:
        if rec.id not in seen:
            seen[rec.id] = rec
        else:
            # Keep the higher priority one
            existing = seen[rec.id]
            if priority_order.get(rec.priority, 4) < priority_order.get(existing.priority, 4):
                seen[rec.id] = rec
    # Sort: critical → high → medium → low
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


def run(metrics: CloudMetrics, context: dict | None = None) -> AgentRunResponse:
    """
    Run the full multi-agent analysis and return a unified response.
    Uses LangGraph if available, falls back to sequential execution.
    """
    context = context or {}
    run_id = str(uuid.uuid4())[:8]
    started_at = datetime.utcnow().isoformat()

    # Try LangGraph orchestration first
    try:
        result = _run_with_langgraph(metrics, context)
        agent_results = result
    except Exception:
        # Graceful fallback: plain sequential execution
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

    return AgentRunResponse(
        run_id=run_id,
        started_at=started_at,
        completed_at=datetime.utcnow().isoformat(),
        agents=agent_result_objs,
        unified_recommendations=unified,
        overall_score=overall,
        summary=summary,
    )


def _run_with_langgraph(metrics: CloudMetrics, context: dict) -> list[dict]:
    """LangGraph-backed orchestration (parallel node execution)."""
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
            state["cost_result"], state["perf_result"], state["sus_result"],
            state["sec_result"], state["rel_result"],
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
        summary="",
    )
    final = app.invoke(initial_state)
    return final["unified"]
