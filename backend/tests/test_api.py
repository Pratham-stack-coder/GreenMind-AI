"""Comprehensive test suite for GreenMind AI backend API."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "timestamp" in data
    assert "demo_mode" in data
    assert data["demo_mode"] is True


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
