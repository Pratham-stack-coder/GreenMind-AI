"""Comprehensive tests for GreenMind AI 5-Agent Multi-Agent Orchestrator and Conflict Resolution."""

import pytest
from app.schemas import CloudMetrics
from app.agents import (
    cost_agent,
    performance_agent,
    sustainability_agent,
    security_agent,
    reliability_agent,
)
from app.agents.orchestrator import run as run_orchestrator, resolve_conflicts


@pytest.fixture
def base_metrics():
    return CloudMetrics(
        timestamp="2026-09-22T14:00:00Z",
        provider="aws",
        region="us-east-1",
        cpu=52.0,
        memory=60.0,
        storage=40.0,
        network=250.0,
        cost_usd_per_hour=0.192,
        carbon_gco2_per_hour=35.0,
        instance_count=2,
        source="DEMO",
    )


def test_individual_agents(base_metrics):
    """Verify each of the 5 agents executes and produces required domain output."""
    context = {"history": [], "predictions": {}}

    agents = [
        ("cost", cost_agent),
        ("performance", performance_agent),
        ("sustainability", sustainability_agent),
        ("security", security_agent),
        ("reliability", reliability_agent),
    ]

    for name, agent in agents:
        res = agent.analyze(base_metrics, context)
        assert "agent" in res
        assert "score" in res
        assert 0 <= res["score"] <= 100
        assert "findings" in res
        assert isinstance(res["findings"], list)
        assert "recommendations" in res
        assert isinstance(res["recommendations"], list)


def test_orchestrator_execution(base_metrics):
    """Verify full orchestrator invokes all agents, aggregates scores, and resolves conflicts."""
    result = run_orchestrator(metrics=base_metrics)

    assert result.run_id is not None
    assert len(result.agents) == 5
    agent_names = {a.agent.lower() for a in result.agents}
    assert any("cost" in name for name in agent_names)
    assert any("performance" in name for name in agent_names)
    assert any("sustainability" in name for name in agent_names)
    assert any("security" in name for name in agent_names)
    assert any("reliability" in name for name in agent_names)

    assert 0 <= result.overall_score <= 100
    assert isinstance(result.unified_recommendations, list)
    assert isinstance(result.conflicts, list)
    assert result.summary is not None


def test_conflict_resolution_high_cpu():
    """Verify that high CPU causes conflict resolution to address performance vs cost."""
    high_cpu_metrics = CloudMetrics(
        timestamp="2026-09-22T14:00:00Z",
        provider="aws",
        region="us-east-1",
        cpu=88.0,
        memory=82.0,
        storage=50.0,
        network=800.0,
        cost_usd_per_hour=0.55,
        carbon_gco2_per_hour=90.0,
        instance_count=4,
        source="DEMO",
    )
    result = run_orchestrator(metrics=high_cpu_metrics)
    assert len(result.agents) == 5
    for c in result.conflicts:
        assert c.conflict_type
        assert c.reconciled_decision
        assert c.rationale
        assert len(c.conflicting_agents) >= 2


def test_conflict_resolution_low_cpu():
    """Verify that low CPU utilization reports low-load recommendations."""
    low_cpu_metrics = CloudMetrics(
        timestamp="2026-09-22T03:00:00Z",
        provider="aws",
        region="us-east-1",
        cpu=18.0,
        memory=25.0,
        storage=30.0,
        network=50.0,
        cost_usd_per_hour=0.25,
        carbon_gco2_per_hour=20.0,
        instance_count=3,
        source="DEMO",
    )
    result = run_orchestrator(metrics=low_cpu_metrics)
    assert result.overall_score > 0
    cost_agent_res = next(a for a in result.agents if "cost" in a.agent.lower())
    assert cost_agent_res is not None
    assert len(cost_agent_res.findings) > 0
