"""
LangGraph Multi-Agent State Definition.
Defines state schemas for cost, performance, sustainability, security,
and reliability agents, as well as the aggregator / conflict resolution node.
"""

from __future__ import annotations

from typing import Any, Optional, TypedDict


class AgentOutput(TypedDict):
    agent: str
    priority: str
    finding: str
    recommendation: str
    reason: str
    confidence: float
    estimated_saving: float
    score: int
    findings: list[str]
    recommendations: list[dict[str, Any]]


class ConflictItem(TypedDict):
    conflict_type: str
    description: str
    conflicting_agents: list[str]
    agent_recommendations: dict[str, str]
    reconciliation_rationale: str
    final_decision: str
    confidence: float


class OrchestratorState(TypedDict):
    metrics: dict[str, Any]
    context: dict[str, Any]
    cost_result: Optional[dict[str, Any]]
    perf_result: Optional[dict[str, Any]]
    sus_result: Optional[dict[str, Any]]
    sec_result: Optional[dict[str, Any]]
    rel_result: Optional[dict[str, Any]]
    unified: list[dict[str, Any]]
    conflicts: list[ConflictItem]
    summary: str
    overall_score: int
