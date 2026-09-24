import asyncio
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.database import (
    init_db,
    persist_telemetry_entry,
    query_telemetry_history,
    record_telemetry,
    get_telemetry_history,
    persist_prediction_entry,
    persist_recommendation_entry,
    persist_agent_result_entry,
    persist_simulation_entry,
    persist_audit_log,
)
from app.routers.telemetry import collect_and_persist_telemetry

client = TestClient(app)


def test_init_db_and_persist_telemetry():
    """Verify database initialization and asynchronous telemetry persistence."""
    async def _run():
        await init_db()

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": "aws",
            "region": "us-east-1",
            "account_id": "123456789012",
            "resource_id": "i-0abcd1234ef56789a",
            "resource_type": "instance",
            "cpu": 42.5,
            "memory": None,  # Guest OS agent not installed
            "storage": None,
            "network": 250.0,
            "network_in": 120.0,
            "network_out": 130.0,
            "cost_usd_per_hour": 0.096,
            "carbon_gco2_per_hour": 18.5,
            "status": "running",
            "source": "LIVE_AWS",
            "memory_source": "UNAVAILABLE",
            "memory_note": "CloudWatch does not report OS memory without CWAgent",
        }
        await persist_telemetry_entry(entry)

        # Query back
        records = await query_telemetry_history(limit=5, provider="aws", region="us-east-1")
        assert len(records) >= 1
        latest = records[0]
        assert latest["provider"] == "aws"
        assert latest["region"] == "us-east-1"
        assert latest["cpu"] == 42.5
        assert latest["memory"] is None
        assert latest["memory_source"] == "UNAVAILABLE"
        assert "CloudWatch" in latest["memory_note"]

    asyncio.run(_run())


def test_all_entity_persist_helpers():
    """Verify persistence helpers for predictions, recommendations, agents, simulations, audit logs."""
    async def _run():
        await init_db()

        # Prediction
        await persist_prediction_entry(
            target="cpu",
            current_value=45.0,
            predicted_value=55.0,
            delta_pct=22.2,
            anomaly=False,
            confidence=0.88,
            horizon_minutes=60,
        )

        # Recommendation
        await persist_recommendation_entry({
            "id": "rec-test-1",
            "category": "cost",
            "priority": "high",
            "title": "Rightsize EC2 instance",
            "description": "Downsize underutilized instance",
            "impact_summary": "Saves $45/mo",
            "estimated_monthly_savings_usd": 45.0,
            "estimated_carbon_reduction_pct": 12.0,
            "effort": "low",
            "action": "resize",
            "evidence": ["CPU avg 8% over 14 days"],
            "confidence": 0.95,
            "status": "open",
        })

        # Agent Result
        await persist_agent_result_entry(
            run_id="run-test-123",
            agent_name="CostOptimizer",
            score=82,
            findings=[{"type": "idle_resource", "severity": "medium"}],
            recommendations_count=2,
        )

        # Simulation
        await persist_simulation_entry(
            sim_id="sim-test-99",
            changes={"instance_type": "t3.medium"},
            before={"cost": 0.096, "cpu": 15.0},
            after={"cost": 0.048, "cpu": 30.0},
            delta={"cost_pct": -50.0},
            risk_score=0.15,
            recommendation="Safe to apply",
            confidence=0.9,
        )

        # Audit Log
        await persist_audit_log(
            rec_id="rec-test-1",
            title="Rightsize EC2 instance",
            action="resize",
            status="applied",
            monthly_savings=45.0,
            carbon_reduction=12.0,
            new_score=85,
            steps_taken=["Triggered AWS ModifyInstanceAttribute"],
            dry_run=False,
        )

    asyncio.run(_run())


def test_collect_and_persist_telemetry_loop():
    """Verify periodic background ingestion function completes without error."""
    async def _run():
        await init_db()
        await collect_and_persist_telemetry()
        history = get_telemetry_history(10)
        assert len(history) > 0

    asyncio.run(_run())


def test_telemetry_history_api():
    """Verify /api/v1/telemetry/history supports filters and granularities."""
    # Seed a metric
    res = client.get("/api/v1/telemetry/live?provider=aws&region=us-east")
    assert res.status_code == 200
    live_data = res.json()
    assert "cpu" in live_data
    assert "source" in live_data

    # Query history
    for gran in ["5m", "15m", "1h", "1d"]:
        resp = client.get(f"/api/v1/telemetry/history?provider=aws&granularity={gran}&limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert "entries" in data
        assert "granularity" in data
        assert data["granularity"] == gran
        assert "count" in data
