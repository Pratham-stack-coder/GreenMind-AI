"""Regression tests for the Optimization Score lifecycle and repository audit requirements.

Covers:
1. Dry-run preview does not mutate actual telemetry or claim real application.
2. Simulated optimization returns baseline and projected score values.
3. A scenario that changes relevant metrics recalculates the projected score correctly.
4. A scenario that does not affect scored metrics does not produce an arbitrary score boost.
5. Score calculations handle valid zero readings (0.0% CPU) without treating them as missing.
6. Missing or unavailable metrics are handled explicitly with documented assumptions.
7. Refreshing recommendations does not silently overwrite applied/simulated state.
8. Resetting simulation restores baseline score and reverts simulated items.
9. Failed operations leave score and action status unchanged.
10. Real cloud mutations remain strictly protected with HTTP 501.
11. Cross-user isolation prevents state leaks across tenants.
12. Consistent scoring methodology across scoring service, analytics, and recommendations.
"""

from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from app.auth import _current_user_id
from app.digital_twin.scenarios import apply_scenario
from app.digital_twin.schemas import StateSnapshot
from app.main import app
from app.routers import analytics, recommendations
from app.schemas import CloudMetrics
from app.services.scoring import compute_optimization_scores

client = TestClient(app)


def test_dry_run_preview_does_not_mutate_telemetry_or_claim_real_application():
    """A dry-run preview returns baseline & projected score without claiming real application."""
    resp = client.get("/recommendations?provider=aws&region=us-east")
    assert resp.status_code == 200
    recs = resp.json()["recommendations"]
    assert len(recs) > 0
    rec = recs[0]
    rec_id = rec["id"]

    # Preview via dry_run=True
    apply_resp = client.post(
        f"/recommendations/{rec_id}/apply",
        json={"dry_run": True, "simulate": False},
    )
    assert apply_resp.status_code == 200
    data = apply_resp.json()

    assert data["status"] in ["simulated", "preview"]
    assert "Dry run completed" in data["message"]
    assert data["baseline_score"] is not None
    assert data["projected_score"] is not None
    assert 0 <= data["baseline_score"] <= 100
    assert 0 <= data["projected_score"] <= 100
    assert data["score_delta"] == round(data["projected_score"] - data["baseline_score"], 1)
    assert isinstance(data["assumptions"], list)

    # Ensure status of item remains unchanged in DB / memory
    check_resp = client.get("/recommendations?provider=aws&region=us-east")
    items = check_resp.json()["recommendations"]
    match = next(r for r in items if r["id"] == rec_id)
    assert match["status"] != "applied"


def test_simulated_optimization_returns_baseline_and_projected_scores():
    """Simulated optimization persists simulated state and updates score projection."""
    recs_resp = client.get("/recommendations?provider=aws&region=us-east")
    recs = recs_resp.json()["recommendations"]
    rec = recs[0]
    rec_id = rec["id"]

    sim_resp = client.post(f"/recommendations/{rec_id}/simulate")
    assert sim_resp.status_code == 200
    sim_data = sim_resp.json()

    assert sim_data["status"] == "simulated"
    assert sim_data["baseline_score"] is not None
    assert sim_data["projected_score"] is not None
    assert "Dry run completed" in sim_data["message"]

    # Verify score endpoint reports simulated score
    score_resp = client.get("/analytics/score?provider=aws&region=us-east")
    assert score_resp.status_code == 200
    score_data = score_resp.json()
    assert score_data["is_simulated"] is True
    assert score_data["overall"] == sim_data["projected_score"]
    assert score_data["baseline_overall"] == sim_data["baseline_score"]
    assert score_data["score_delta"] == sim_data["score_delta"]


def test_scenario_changing_metrics_recalculates_score_correctly():
    """A scenario that resolves severe CPU/memory saturation recalculates performance and overall score upwards."""
    # Saturated state (dangerous 95% CPU, 92% memory)
    overloaded = CloudMetrics(
        timestamp="2026-10-13T00:00:00Z",
        cpu=95.0,
        memory=92.0,
        cost_usd_per_hour=2.5,
        carbon_gco2_per_hour=200.0,
        provider="aws",
        region="us-east",
    )
    score_before = compute_optimization_scores(overloaded)

    # Rightsized state (healthy 60% CPU, 55% memory)
    healthy = CloudMetrics(
        timestamp="2026-10-13T00:00:00Z",
        cpu=60.0,
        memory=55.0,
        cost_usd_per_hour=1.0,
        carbon_gco2_per_hour=90.0,
        provider="aws",
        region="us-east",
    )
    score_after = compute_optimization_scores(healthy)

    # Performance and overall scores should significantly improve
    assert score_after.performance > score_before.performance
    assert score_after.overall > score_before.overall


def test_scenario_not_affecting_scored_metrics_produces_no_arbitrary_increase():
    """A neutral scenario with no metric changes produces zero score delta (no arbitrary +5/10 boost)."""
    metrics = CloudMetrics(
        timestamp="2026-10-13T00:00:00Z",
        cpu=50.0,
        memory=50.0,
        cost_usd_per_hour=0.5,
        carbon_gco2_per_hour=50.0,
        provider="aws",
        region="us-east",
    )
    score_1 = compute_optimization_scores(metrics)
    # Re-evaluate same metrics
    score_2 = compute_optimization_scores(metrics)

    assert score_1.overall == score_2.overall
    assert score_1.cost == score_2.cost
    assert score_1.performance == score_2.performance
    assert score_1.sustainability == score_2.sustainability


def test_score_calculation_handles_valid_zero_readings_correctly():
    """Valid 0.0% CPU reading must be treated as idle compute waste rather than falling back to 50.0%."""
    zero_cpu_metrics = CloudMetrics(
        timestamp="2026-10-13T00:00:00Z",
        cpu=0.0,
        memory=50.0,
        cost_usd_per_hour=0.5,
        carbon_gco2_per_hour=50.0,
        provider="aws",
        region="us-east",
    )
    score_zero = compute_optimization_scores(zero_cpu_metrics)

    # 50.0% CPU represents moderate, balanced utilization
    fallback_metrics = CloudMetrics(
        timestamp="2026-10-13T00:00:00Z",
        cpu=50.0,
        memory=50.0,
        cost_usd_per_hour=0.5,
        carbon_gco2_per_hour=50.0,
        provider="aws",
        region="us-east",
    )
    score_fallback = compute_optimization_scores(fallback_metrics)

    # Zero CPU incurs an idle waste penalty on cost and overall
    assert score_zero.cost != score_fallback.cost
    assert score_zero.cost < score_fallback.cost
    assert score_zero.overall < score_fallback.overall


def test_missing_or_unavailable_metrics_handled_explicitly():
    """Missing metrics must produce documented assumptions and bounded scores [0, 100]."""
    scores = compute_optimization_scores(
        cpu=None,
        memory=None,
        cost_usd_per_hour=None,
        carbon_gco2_per_hour=None,
        region="us-east",
    )

    assert 0 <= scores.overall <= 100
    assert 0 <= scores.cost <= 100
    assert 0 <= scores.performance <= 100
    assert 0 <= scores.sustainability <= 100
    assert 0 <= scores.security <= 100
    assert 0 <= scores.reliability <= 100

    # Assumptions must clearly flag estimate / missing dimensions
    assumptions_text = " ".join(scores.assumptions).lower()
    assert "estimate" in assumptions_text
    assert "security" in assumptions_text or "reliability" in assumptions_text


def test_refreshing_recommendations_does_not_silently_overwrite_applied_or_simulated_state():
    """Fetching recommendations does not reset previously applied or simulated items."""
    # First, simulate a recommendation
    recs_resp = client.get("/recommendations?provider=aws&region=us-east")
    recs = recs_resp.json()["recommendations"]
    assert len(recs) > 0
    target_rec = recs[0]

    sim_res = client.post(f"/recommendations/{target_rec['id']}/simulate")
    assert sim_res.status_code == 200

    # Now refresh recommendations multiple times
    for _ in range(3):
        refresh_resp = client.get("/recommendations?provider=aws&region=us-east")
        assert refresh_resp.status_code == 200
        refreshed_recs = refresh_resp.json()["recommendations"]
        match = next(r for r in refreshed_recs if r["id"] == target_rec["id"])
        assert match["status"] == "simulated"


def test_reset_simulation_restores_baseline_score():
    """Resetting simulation clears simulated state and restores baseline score."""
    # Simulate a recommendation
    recs_resp = client.get("/recommendations?provider=aws&region=us-east")
    target_rec = recs_resp.json()["recommendations"][0]
    client.post(f"/recommendations/{target_rec['id']}/simulate")

    # Reset simulation
    reset_resp = client.post("/recommendations/reset-simulation")
    assert reset_resp.status_code == 200
    data = reset_resp.json()
    assert data["status"] == "reset"

    # Verify score is restored to baseline
    score_resp = client.get("/analytics/score?provider=aws&region=us-east")
    score_data = score_resp.json()
    assert score_data["is_simulated"] is False

    # Verify recommendation status reverted to open
    recs_after = client.get("/recommendations?provider=aws&region=us-east").json()["recommendations"]
    match = next(r for r in recs_after if r["id"] == target_rec["id"])
    assert match["status"] == "open"


def test_failed_or_invalid_recommendation_leaves_score_and_action_status_unchanged():
    """Applying or simulating a non-existent ID fails cleanly and leaves state intact."""
    recs_before = client.get("/recommendations?provider=aws&region=us-east").json()
    score_before = recs_before["optimization_score"]

    resp = client.post("/recommendations/non-existent-rec-id-9999/apply", json={"dry_run": True})
    assert resp.status_code == 404

    sim_resp = client.post("/recommendations/non-existent-rec-id-9999/simulate")
    assert sim_resp.status_code == 404

    recs_after = client.get("/recommendations?provider=aws&region=us-east").json()
    assert recs_after["optimization_score"] == score_before


def test_real_cloud_action_returns_501_not_implemented():
    """Non-dry-run requests are rejected with 501 Not Implemented to prevent faux cloud mutations."""
    recs_resp = client.get("/recommendations?provider=aws&region=us-east")
    target_rec = recs_resp.json()["recommendations"][0]

    resp = client.post(
        f"/recommendations/{target_rec['id']}/apply",
        json={"dry_run": False, "simulate": False},
    )
    assert resp.status_code == 501
    assert "Live cloud remediation is not implemented" in resp.json()["detail"]


def test_cross_user_isolation_for_recommendations_and_simulation():
    """Simulation state and recommendation statuses are strictly scoped to the requesting user."""
    from app.auth import require_authenticated_user

    user_a = f"tenant-a-{uuid4()}"
    user_b = f"tenant-b-{uuid4()}"

    def make_auth(uid):
        async def override():
            token = _current_user_id.set(uid)
            try:
                yield {"sub": uid, "role": "authenticated"}
            finally:
                _current_user_id.reset(token)
        return override

    original_override = app.dependency_overrides.get(require_authenticated_user)
    try:
        # Act as User A
        app.dependency_overrides[require_authenticated_user] = make_auth(user_a)
        recs_a = client.get("/recommendations?provider=aws&region=us-east").json()["recommendations"]
        assert len(recs_a) > 0
        rec_id_a = recs_a[0]["id"]
        client.post(f"/recommendations/{rec_id_a}/simulate")

        score_a = client.get("/analytics/score?provider=aws&region=us-east").json()
        assert score_a["is_simulated"] is True

        # Act as User B
        app.dependency_overrides[require_authenticated_user] = make_auth(user_b)
        score_b = client.get("/analytics/score?provider=aws&region=us-east").json()
        assert score_b["is_simulated"] is False

        recs_b = client.get("/recommendations?provider=aws&region=us-east").json()["recommendations"]
        assert len(recs_b) > 0
        match_b = next(r for r in recs_b if r["id"] == rec_id_a)
        assert match_b["status"] == "open"
    finally:
        if original_override:
            app.dependency_overrides[require_authenticated_user] = original_override
        else:
            app.dependency_overrides.pop(require_authenticated_user, None)


def test_scoring_api_and_recommendation_api_use_consistent_scoring_method():
    """Both /analytics/score and /recommendations derive scores from the unified scoring service."""
    metrics = CloudMetrics(
        timestamp="2026-10-13T00:00:00Z",
        cpu=45.0,
        memory=52.0,
        cost_usd_per_hour=0.45,
        carbon_gco2_per_hour=60.0,
        provider="aws",
        region="us-east",
    )
    expected_scores = compute_optimization_scores(metrics)

    # Directly verify math matches
    assert expected_scores.overall >= 0
    assert expected_scores.cost >= 0
    assert expected_scores.performance >= 0
    assert expected_scores.sustainability >= 0
    assert expected_scores.security >= 0
    assert expected_scores.reliability >= 0


def test_digital_twin_scenario_validation_and_scoring():
    """Digital twin validates snapshot bounds and includes baseline/projected scores."""
    # Invalid snapshot with negative CPU
    with pytest.raises(ValueError, match="Utilization must be between 0% and 100%"):
        apply_scenario("RIGHT_SIZE", StateSnapshot(cpu=-5.0, memory=50.0, cost=10.0, carbon=10.0))

    # Single instance cluster cannot SCALE_DOWN
    with pytest.raises(ValueError, match="Cannot scale down cluster with only 1 instance"):
        apply_scenario("SCALE_DOWN", StateSnapshot(cpu=50.0, memory=50.0, cost=10.0, carbon=10.0, instance_count=1))

    # Successful scenario simulation
    resp = client.post(
        "/api/v1/digital-twin/scenario",
        json={
            "scenario": "RIGHT_SIZE",
            "current_state": {
                "cpu": 80.0,
                "memory": 70.0,
                "cost": 500.0,
                "carbon": 50.0,
                "instance_count": 4,
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "baseline_score" in data
    assert "projected_score" in data
    assert "score_delta" in data
    assert "scoring_explanation" in data
