"""Comprehensive tests for AI Cloud Copilot agent, tool invocation, and action dispatch."""

import pytest
from app.copilot.agent import CopilotAgent
from app.copilot.schemas import CopilotChatRequest
from app.copilot import tools


def test_copilot_all_tools():
    """Verify all 8 Copilot tools execute and return valid telemetry structures."""
    metrics = tools.get_cloud_metrics("aws", "us-east-1")
    assert "cpu" in metrics
    assert "cost_usd_per_hour" in metrics

    history = tools.get_history(limit=5)
    assert isinstance(history, list)

    preds = tools.get_predictions(cpu=55.0)
    assert "cpu" in preds

    cost = tools.get_cost_analysis(days=7)
    assert "total_usd" in cost

    carbon = tools.get_carbon_analysis(days=7, region="us-east")
    assert "total_gco2" in carbon

    recs = tools.get_recommendations("aws", "us-east-1")
    assert isinstance(recs, list)

    health = tools.get_cloud_health("aws", "us-east-1")
    assert "health_score" in health

    sim = tools.run_digital_twin_simulation("RIGHT_SIZE", cpu=75.0)
    assert sim.get("scenario") == "RIGHT_SIZE"


def test_copilot_cost_intent():
    """Verify cost-related query dispatches cost tools and generates actionable recommendations."""
    agent = CopilotAgent()
    req = CopilotChatRequest(
        message="Why is my AWS cost so high and how can I save money?",
        provider="aws",
        region="us-east-1",
    )
    res = agent.process_message(req)
    assert res.answer or res.reply
    assert "cost_analysis" in res.sources
    assert len(res.actions) > 0
    assert any("scenario" in a.endpoint.lower() or "recommendation" in a.endpoint.lower() for a in res.actions)


def test_copilot_carbon_intent():
    """Verify sustainability query retrieves carbon curve and recommends green hours."""
    agent = CopilotAgent()
    req = CopilotChatRequest(
        message="How clean is the energy grid and what are my Scope 2 emissions?",
        provider="aws",
        region="us-east-1",
    )
    res = agent.process_message(req)
    assert res.answer or res.reply
    assert "carbon_analysis" in res.sources
    assert len(res.follow_up_suggestions) > 0


def test_copilot_forecast_intent():
    """Verify capacity planning query retrieves ML predictions and evaluates saturation risk."""
    agent = CopilotAgent()
    req = CopilotChatRequest(
        message="Forecast CPU workload and capacity saturation risk for next hour",
        provider="aws",
        region="us-east-1",
    )
    res = agent.process_message(req)
    assert res.answer or res.reply
    assert "predictions" in res.sources


def test_copilot_simulation_intent():
    """Verify simulation query triggers Digital Twin simulator and returns estimated impact."""
    agent = CopilotAgent()
    req = CopilotChatRequest(
        message="Simulate right-sizing my cluster and estimate the monthly savings",
        provider="aws",
        region="us-east-1",
    )
    res = agent.process_message(req)
    assert res.answer or res.reply
    assert "digital_twin_simulation" in res.sources
    assert any("simulate" in a.label.lower() or "right-size" in a.label.lower() for a in res.actions)
