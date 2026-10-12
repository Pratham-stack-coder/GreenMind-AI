"""Comprehensive test suite for GreenMind AI backend API."""

import pytest
from fastapi.testclient import TestClient
from app.main import app, settings

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "timestamp" in data
    assert "demo_mode" in data
    assert data["demo_mode"] == settings.demo_mode


def test_cloud_metrics():
    response = client.get("/cloud-metrics?region=us-east")
    assert response.status_code == 200
    data = response.json()
    assert "cpu" in data
    assert "memory" in data
    assert "storage" in data
    assert "network" in data
    assert data["source"] in ["DEMO", "LIVE", "LIVE_AWS"]


def test_predict():
    response = client.post("/predict?cpu=55.0&hour=14.0&day_of_week=2")
    assert response.status_code == 200
    data = response.json()
    assert "current_cpu" in data
    assert "predicted_cpu" in data
    assert "risk" in data
    assert data["risk"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def test_predictions_endpoint():
    response = client.get("/predictions?provider=aws&region=us-east")
    assert response.status_code == 200
    data = response.json()
    assert "cpu" in data
    assert "memory" in data
    assert "network" in data
    assert "cost" in data
    assert "carbon" in data
    assert "predicted" in data["cpu"]


def test_analytics():
    response = client.get("/analytics?days=7&provider=aws&region=us-east")
    assert response.status_code == 200
    data = response.json()
    assert "cost" in data
    assert "carbon" in data
    assert "scores" in data
    assert data["scores"]["overall"] >= 0


def test_cost_analysis():
    response = client.get("/cost-analysis?days=7")
    assert response.status_code == 200
    data = response.json()
    assert "total_usd" in data
    assert "data_points" in data
    assert "top_cost_drivers" in data


def test_carbon_analysis():
    response = client.get("/carbon-analysis?days=7&region=us-east")
    assert response.status_code == 200
    data = response.json()
    assert "total_gco2" in data
    assert "green_hours_pct" in data


def test_recommendations():
    response = client.get("/recommendations?provider=aws&region=us-east")
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert isinstance(data["recommendations"], list)
    assert "optimization_score" in data


def test_explain_recommendation():
    # First fetch recommendations to get an ID
    recs_resp = client.get("/recommendations?provider=aws&region=us-east")
    assert recs_resp.status_code == 200
    recs = recs_resp.json()["recommendations"]
    if recs:
        rec_id = recs[0]["id"]
        explain_resp = client.get(f"/api/v1/recommendations/{rec_id}/explain")
        assert explain_resp.status_code == 200
        data = explain_resp.json()
        assert "why_flagged" in data
        assert "what_detected" in data
        assert "expected_impact" in data


def test_agents_list():
    response = client.get("/agents")
    assert response.status_code == 200
    data = response.json()
    assert "agents" in data
    assert len(data["agents"]) == 5
    assert "conflict_resolution" in data


def test_agents_run():
    payload = {"provider": "aws", "region": "us-east"}
    response = client.post("/agents/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert "agents" in data
    assert len(data["agents"]) == 5  # Cost, Performance, Sustainability, Security, Reliability
    assert "unified_recommendations" in data
    assert 0 <= data["overall_score"] <= 100
    assert "conflicts" in data
    assert isinstance(data["conflicts"], list)


def test_digital_twin_simulate():
    payload = {
        "baseline_metrics": {
            "timestamp": "2026-09-22T00:00:00Z",
            "provider": "aws",
            "region": "us-east",
            "cpu": 50.0,
            "memory": 60.0,
            "storage": 40.0,
            "network": 450.0,
            "cost_usd_per_hour": 0.192,
            "carbon_gco2_per_hour": 35.0,
            "instance_count": 2,
            "source": "DEMO",
        },
        "changes": [
            {
                "action": "resize",
                "instance_type_from": "m5.xlarge",
                "instance_type_to": "m5.large",
            }
        ],
        "simulation_hours": 24.0,
    }
    response = client.post("/digital-twin/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "simulation_id" in data
    assert "before" in data
    assert "after" in data
    assert "delta" in data
    assert "confidence" in data


def test_digital_twin_scenario():
    payload = {
        "scenario": "RIGHT_SIZE",
        "current_state": {
            "cpu": 80.0,
            "memory": 65.0,
            "cost": 1000.0,
            "carbon": 6.2,
            "instance_count": 4,
            "monthly_cost": 1000.0,
            "monthly_carbon_kg": 6.2,
        },
    }
    response = client.post("/api/v1/digital-twin/scenario", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["scenario"] == "RIGHT_SIZE"
    assert data["is_simulated"] is True
    assert data["estimated_saving"] > 0
    assert data["risk"] in ["LOW", "MEDIUM", "HIGH"]


def test_copilot_chat():
    payload = {
        "message": "Why is my cloud cost high?",
        "provider": "aws",
        "region": "us-east",
    }
    response = client.post("/copilot/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data or "answer" in data
    assert len(data.get("reply", "") or data.get("answer", "")) > 0
    assert "sources" in data
    assert isinstance(data["sources"], list)
    assert "actions" in data


def test_cloud_providers():
    response = client.get("/cloud/providers")
    assert response.status_code == 200
    data = response.json()
    assert "providers" in data
    provider_ids = [p["id"] for p in data["providers"]]
    assert "aws" in provider_ids
    assert "azure" in provider_ids
    assert "gcp" in provider_ids


def test_cloud_resources():
    response = client.get("/cloud/resources?provider=aws&region=us-east")
    assert response.status_code == 200
    data = response.json()
    assert "resources" in data
    assert isinstance(data["resources"], list)
    assert len(data["resources"]) > 0


def test_prometheus_metrics():
    response = client.get("/metrics/prometheus")
    assert response.status_code == 200
    assert "greenmind_api_requests_total" in response.text
    assert "greenmind_cloud_collections_total" in response.text


def test_cors_vercel_origin():
    """Verify a configured Vercel origin receives CORS headers with credentials."""
    response = client.get("/health", headers={"Origin": "https://green-mind-ai-ten.vercel.app"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://green-mind-ai-ten.vercel.app"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_preflight_options():
    """Verify OPTIONS preflight from a configured deployment origin."""
    response = client.options(
        "/api/v1/telemetry/live",
        headers={
            "Origin": "https://green-mind-ai-ten.vercel.app",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://green-mind-ai-ten.vercel.app"
    assert "GET" in response.headers.get("access-control-allow-methods", "")


def test_telemetry_provider_status():
    """Verify provider connectivity status endpoint."""
    response = client.get("/api/v1/telemetry/provider-status")
    assert response.status_code == 200
    data = response.json()
    assert "providers" in data
    assert "aws" in data["providers"]
    assert "azure" in data["providers"]
    assert "gcp" in data["providers"]


def test_agent_execution_trace():
    """Verify that multi-agent execution emits detailed LangGraph node traces."""
    response = client.post("/api/v1/agents/run", json={"provider": "aws", "region": "us-east"})
    assert response.status_code == 200
    data = response.json()
    assert "execution_trace" in data
    assert len(data["execution_trace"]) >= 5
    step1 = data["execution_trace"][0]
    assert "step_number" in step1
    assert "agent" in step1
    assert "execution_ms" in step1
    assert "thoughts" in step1


def test_digital_twin_latency_and_risk():
    """Verify that digital twin computes M/M/1 queueing latency and risk scores."""
    req_body = {
        "baseline_metrics": {
            "timestamp": "2026-10-11T00:00:00Z",
            "provider": "aws",
            "region": "us-east",
            "cpu": 65.0,
            "memory": 60.0,
            "storage": 50.0,
            "network": 400.0,
            "cost_usd_per_hour": 0.22,
            "carbon_gco2_per_hour": 150.0,
            "instance_count": 2,
        },
        "changes": [
            {"action": "resize", "instance_type_to": "m5.large"}
        ],
        "simulation_hours": 24.0,
    }
    response = client.post("/api/v1/digital-twin/simulate", json=req_body)
    assert response.status_code == 200
    data = response.json()
    assert "before" in data
    assert "after" in data
    assert "p95_latency_ms" in data["before"]
    assert "risk_score" in data["before"]
    assert "risk_factors" in data["before"]
    assert "p95_latency_pct" in data["delta"]


def test_explain_quantitative_evidence():
    """Verify that recommendation explanation returns quantitative telemetry comparisons."""
    recs_res = client.get("/api/v1/recommendations?provider=aws&region=us-east")
    assert recs_res.status_code == 200
    recs = recs_res.json()["recommendations"]
    assert len(recs) > 0
    rec_id = recs[0]["id"]

    exp_res = client.get(f"/api/v1/recommendations/{rec_id}/explain")
    assert exp_res.status_code == 200
    exp_data = exp_res.json()
    assert "data_evidence" in exp_data
    assert len(exp_data["data_evidence"]) > 0
    assert "metric" in exp_data["data_evidence"][0]
    assert "observed" in exp_data["data_evidence"][0]
    assert "counterfactual" in exp_data


def test_recommendation_apply_and_rollback_flow():
    """Verify dry-run previews and that unimplemented live actions fail clearly."""
    recs_res = client.get("/api/v1/recommendations?provider=aws&region=us-east")
    assert recs_res.status_code == 200
    recs = recs_res.json()["recommendations"]
    assert len(recs) > 0
    rec_id = recs[0]["id"]

    # Dry-run preview is explicitly simulated and does not mark the item applied.
    sim_res = client.post(f"/api/v1/recommendations/{rec_id}/apply", json={"dry_run": True})
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["status"] == "simulated"
    assert sim_data["dry_run"] is True
    assert "No cloud resources were changed" in sim_data["message"]

    applied_list = client.get("/api/v1/recommendations/applied")
    assert applied_list.status_code == 200
    assert applied_list.json() == []

    # Live mutation and rollback are not implemented.
    apply_res = client.post(f"/api/v1/recommendations/{rec_id}/apply", json={"dry_run": False})
    assert apply_res.status_code == 501
    assert "Live cloud remediation is not implemented" in apply_res.json()["detail"]

    rollback_res = client.post(f"/api/v1/recommendations/{rec_id}/rollback")
    assert rollback_res.status_code == 501
    assert "rollback is not implemented" in rollback_res.json()["detail"]



