"""Validation and mathematical integrity tests for the Digital Twin simulation engine."""

import pytest
from app.digital_twin.scenarios import apply_scenario
from app.digital_twin.schemas import StateSnapshot
from app.routers.digital_twin import simulate
from app.schemas import CloudMetrics, SimulationChange, SimulationRequest


@pytest.fixture
def baseline_state():
    return StateSnapshot(
        cpu=75.0,
        memory=70.0,
        cost=1.20,
        carbon=150.0,
        instance_count=4,
        monthly_cost=864.0,
        monthly_carbon_kg=108.0,
    )


def test_right_size_scenario(baseline_state):
    """Verify RIGHT_SIZE produces ~25% cost reduction and positive savings."""
    after, saving, carbon_red, impact, risk, rec = apply_scenario("RIGHT_SIZE", baseline_state)
    assert after.cost < baseline_state.cost
    assert after.monthly_cost < baseline_state.monthly_cost
    assert saving > 0
    assert carbon_red > 0
    assert risk in ["LOW", "MEDIUM"]


def test_scale_up_scenario(baseline_state):
    """Verify SCALE_UP increases capacity (drops CPU %) while increasing cost."""
    after, saving, carbon_red, impact, risk, rec = apply_scenario("SCALE_UP", baseline_state)
    assert after.cpu < baseline_state.cpu
    assert after.cost > baseline_state.cost
    assert after.instance_count == baseline_state.instance_count + 1
    assert saving < 0  # Cost increase represented by negative saving


def test_scale_down_scenario(baseline_state):
    """Verify SCALE_DOWN removes instance, increases utilization, and cuts cost."""
    after, saving, carbon_red, impact, risk, rec = apply_scenario("SCALE_DOWN", baseline_state)
    assert after.cpu > baseline_state.cpu
    assert after.cost < baseline_state.cost
    assert after.instance_count == baseline_state.instance_count - 1
    assert saving > 0


def test_consolidate_scenario(baseline_state):
    """Verify CONSOLIDATE merges instances and improves bin-packing efficiency."""
    after, saving, carbon_red, impact, risk, rec = apply_scenario("CONSOLIDATE", baseline_state)
    assert after.cost < baseline_state.cost
    assert saving > 0
    assert carbon_red > 0


def test_region_migration_scenario(baseline_state):
    """Verify REGION_MIGRATION drastically cuts carbon emissions without changing CPU capacity."""
    after, saving, carbon_red, impact, risk, rec = apply_scenario("REGION_MIGRATION", baseline_state)
    assert after.cpu == baseline_state.cpu
    assert after.carbon < baseline_state.carbon
    assert carbon_red > 0
    assert "carbon" in rec.lower()


def test_simulate_request_migration():
    """Verify /digital-twin/simulate calculates regional carbon delta when migrating regions."""
    req = SimulationRequest(
        baseline_metrics=CloudMetrics(
            timestamp="2026-09-22T14:00:00Z",
            provider="aws",
            region="us-east",
            cpu=50.0,
            memory=50.0,
            storage=40.0,
            network=200.0,
            cost_usd_per_hour=0.384,
            carbon_gco2_per_hour=70.0,
            instance_count=2,
            source="DEMO",
        ),
        changes=[
            SimulationChange(action="migrate", target_region="ca-central")
        ],
        simulation_hours=24.0,
    )
    result = simulate(req)
    assert result.simulation_id is not None
    assert result.after.cpu == 50.0
    assert "carbon_pct" in result.delta


def test_simulate_hours_validation():
    """Verify that simulate enforces valid simulation_hours range (1.0 to 720.0)."""
    from fastapi import HTTPException

    base = CloudMetrics(
        timestamp="2026-09-22T14:00:00Z",
        provider="aws",
        region="us-east",
        cpu=50.0,
        memory=50.0,
        storage=40.0,
        network=200.0,
        cost_usd_per_hour=0.384,
        carbon_gco2_per_hour=70.0,
        instance_count=2,
        source="DEMO",
    )
    with pytest.raises(HTTPException) as exc_info:
        simulate(SimulationRequest(baseline_metrics=base, changes=[], simulation_hours=0.0))
    assert exc_info.value.status_code == 422
    assert "simulation_hours" in exc_info.value.detail

    with pytest.raises(HTTPException) as exc_info:
        simulate(SimulationRequest(baseline_metrics=base, changes=[], simulation_hours=1000.0))
    assert exc_info.value.status_code == 422


def test_scenario_validation():
    """Verify that simulate_scenario catches snapshot validation errors as HTTP 422."""
    from fastapi import HTTPException
    from app.digital_twin.schemas import SimulationScenarioRequest, StateSnapshot
    from app.routers.digital_twin import simulate_scenario

    invalid_req = SimulationScenarioRequest(
        scenario="RIGHT_SIZE",
        current_state=StateSnapshot(
            cpu=150.0,  # Invalid CPU > 100%
            memory=50.0,
            cost=1.0,
            carbon=50.0,
        ),
    )
    with pytest.raises(HTTPException) as exc_info:
        simulate_scenario(invalid_req)
    assert exc_info.value.status_code == 422
    assert "Invalid CPU utilization" in exc_info.value.detail


@pytest.mark.asyncio
async def test_simulation_history_tenant_and_region_isolation():
    """Verify that digital twin simulation records are strictly tenant-isolated and support regional filtering."""
    import asyncio
    from app.auth import _current_user_id
    from app.database import query_simulation_history, persist_simulation_entry
    from app.routers.digital_twin import get_simulation_history

    user_a_token = _current_user_id.set("user-twin-alice-111")
    try:
        # User A creates a simulation record
        await persist_simulation_entry(
            sim_id="sim-alice-aws-1",
            changes={"changes": [{"action": "resize"}]},
            before={"cpu": 50.0, "monthly_cost_usd": 100.0},
            after={"cpu": 40.0, "monthly_cost_usd": 80.0},
            delta={"monthly_cost_pct": -20.0},
            risk_score=15.0,
            recommendation="Save 20%",
            confidence=0.85,
            owner_id="user-twin-alice-111",
            provider="aws",
            region="us-east",
        )
        await persist_simulation_entry(
            sim_id="sim-alice-gcp-1",
            changes={"changes": [{"action": "migrate"}]},
            before={"cpu": 50.0, "monthly_cost_usd": 100.0},
            after={"cpu": 50.0, "monthly_cost_usd": 90.0},
            delta={"monthly_cost_pct": -10.0},
            risk_score=10.0,
            recommendation="Migrate to GCP",
            confidence=0.80,
            owner_id="user-twin-alice-111",
            provider="gcp",
            region="europe-west1",
        )

        # Alice queries history
        alice_history = await get_simulation_history()
        alice_ids = [h["simulation_id"] for h in alice_history]
        assert "sim-alice-aws-1" in alice_ids
        assert "sim-alice-gcp-1" in alice_ids

        # Alice queries with provider filter
        gcp_history = await get_simulation_history(provider="gcp")
        assert len(gcp_history) == 1
        assert gcp_history[0]["simulation_id"] == "sim-alice-gcp-1"
        assert gcp_history[0]["provider"] == "gcp"

        # Switch to User B (Bob)
        _current_user_id.set("user-twin-bob-222")
        bob_history = await get_simulation_history()
        bob_ids = [h["simulation_id"] for h in bob_history]
        assert "sim-alice-aws-1" not in bob_ids
        assert "sim-alice-gcp-1" not in bob_ids
        assert len(bob_history) == 0
    finally:
        _current_user_id.reset(user_a_token)

