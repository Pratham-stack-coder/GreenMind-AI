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


def test_regions():
    response = client.get("/api/v1/regions")
    assert response.status_code == 200
    data = response.json()
    assert "regions" in data
    assert "us-east" in data["regions"]
    assert "ca-central" in data["regions"]


def test_carbon_curve():
    response = client.get("/api/v1/carbon-curve?region=us-east")
    assert response.status_code == 200
    data = response.json()
    assert data["region"] == "us-east"
    assert "curve" in data
    assert len(data["curve"]) == 24
    assert "green_score" in data


def test_telemetry_live():
    response = client.get("/api/v1/telemetry/live?provider=aws&region=us-east")
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "aws"
    assert data["region"] == "us-east"
    assert 0 <= data["cpu"] <= 100
    assert 0 <= data["memory"] <= 100
    assert data["cost_usd_per_hour"] > 0
    assert data["carbon_gco2_per_hour"] > 0


def test_predictions_forecast():
    payload = {
        "cpu": 65.0,
        "memory": 70.0,
        "network": 300.0,
        "provider": "aws",
        "region": "us-east",
    }
    response = client.post("/api/v1/predictions/forecast", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "cpu" in data
    assert "memory" in data
    assert "network" in data
    assert "cost_usd_per_hour" in data
    assert "carbon_gco2_per_hour" in data
    assert data["risk"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert data["horizon_minutes"] == 60


def test_recommendations():
    response = client.get("/api/v1/recommendations?provider=aws&region=us-east")
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert isinstance(data["recommendations"], list)
    assert "optimization_score" in data


def test_agents_run():
    payload = {"provider": "aws", "region": "us-east"}
    response = client.post("/api/v1/agents/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert "agents" in data
    assert "agent_results" in data
    assert len(data["agents"]) == 5  # Cost, Performance, Sustainability, Security, Reliability
    assert len(data["agent_results"]) == 5
    assert "unified_recommendations" in data
    assert 0 <= data["overall_score"] <= 100
    assert "summary" in data


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
    response = client.post("/api/v1/digital-twin/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "simulation_id" in data
    assert "before" in data
    assert "after" in data
    assert "delta" in data
    assert "confidence" in data


def test_copilot_chat():
    payload = {
        "message": "How can I reduce carbon emissions on AWS?",
        "provider": "aws",
        "region": "us-east",
    }
    response = client.post("/api/v1/copilot/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert len(data["reply"]) > 0
    assert "actions" in data
    assert "follow_up_suggestions" in data


def test_copilot_suggestions():
    response = client.get("/api/v1/copilot/suggestions")
    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data
    assert len(data["suggestions"]) > 0


def test_analytics_score():
    response = client.get("/api/v1/analytics/score?provider=aws&region=us-east")
    assert response.status_code == 200
    data = response.json()
    assert "overall" in data
    assert "cost" in data
    assert "performance" in data
    assert "sustainability" in data
    assert "security" in data
    assert "reliability" in data
    assert data["trend"] in ["improving", "stable", "declining"]


def test_recommendation_apply_flow():
    # 1. Fetch recommendations to ensure there is at least one
    res = client.get("/api/v1/recommendations?provider=aws&region=us-east")
    assert res.status_code == 200
    recs = res.json()["recommendations"]
    assert len(recs) > 0
    rec_id = recs[0]["id"]

    # 2. Test Dry Run apply
    dry_res = client.post(f"/api/v1/recommendations/{rec_id}/apply", json={"dry_run": True})
    assert dry_res.status_code == 200
    dry_data = dry_res.json()
    assert dry_data["status"] == "simulated"
    assert dry_data["dry_run"] is True
    assert len(dry_data["steps_taken"]) > 0

    # 3. Test Live apply
    apply_res = client.post(f"/api/v1/recommendations/{rec_id}/apply", json={"dry_run": False})
    assert apply_res.status_code == 200
    apply_data = apply_res.json()
    assert apply_data["status"] == "applied"
    assert apply_data["recommendation_id"] == rec_id
    assert len(apply_data["steps_taken"]) > 0
    assert apply_data["new_score"] is not None

    # 4. Verify recommendation status updated to 'applied'
    res_after = client.get("/api/v1/recommendations?status=applied")
    assert res_after.status_code == 200
    applied_list = res_after.json()["recommendations"]
    assert any(r["id"] == rec_id for r in applied_list)

    # 5. Verify /applied history endpoint
    hist_res = client.get("/api/v1/recommendations/applied")
    assert hist_res.status_code == 200
    hist_items = hist_res.json()
    assert any(h["recommendation_id"] == rec_id for h in hist_items)

    # 6. Test Rollback
    rollback_res = client.post(f"/api/v1/recommendations/{rec_id}/rollback")
    assert rollback_res.status_code == 200
    rollback_data = rollback_res.json()
    assert rollback_data["status"] == "rolled_back"

    # 7. Test Batch apply
    batch_res = client.post("/api/v1/recommendations/apply-batch", json={"priority": "critical"})
    assert batch_res.status_code == 200
    batch_data = batch_res.json()
    assert "applied_count" in batch_data
    assert "results" in batch_data

