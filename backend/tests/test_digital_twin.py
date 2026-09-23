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
