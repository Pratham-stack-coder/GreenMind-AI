"""Security regression tests for unauthenticated access and exact CORS allowlists."""
from fastapi.testclient import TestClient
from app.auth import require_authenticated_user
from app.main import app, settings
from app.config import Settings


def test_protected_route_rejects_missing_token_without_dependency_override():
    previous = app.dependency_overrides.pop(require_authenticated_user, None)
    try:
        response = TestClient(app).get("/api/v1/auth/session")
        assert response.status_code == 401
    finally:
        if previous is not None:
            app.dependency_overrides[require_authenticated_user] = previous


def test_cors_allowlist_requires_exact_origins():
    config = Settings(
        allowed_origins="http://localhost:5173,https://greenmind-ai.vercel.app",
        cors_origins="https://app.example.com;https://admin.example.com/",
    )
    allowed = config.get_allowed_origins()
    assert allowed == [
        "http://localhost:5173",
        "https://greenmind-ai.vercel.app",
        "https://app.example.com",
        "https://admin.example.com",
    ]
    assert "https://attacker.vercel.app" not in allowed


def test_cors_rejects_unlisted_browser_origin():
    response = TestClient(app).options(
        "/api/v1/auth/session",
        headers={
            "Origin": "https://attacker.vercel.app",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert response.headers.get("access-control-allow-origin") != "https://attacker.vercel.app"


def test_unauthenticated_recommendation_mutation_is_denied():
    # This verifies the authentication boundary only; it does not prove per-user isolation.
    # The repository's shared recommendation store still needs an owner-scoped redesign.
    from app.routers import recommendations as recommendations_router

    previous_recs = recommendations_router._last_recommendations
    previous_applied = recommendations_router._applied_recommendations
    previous_dismissed = recommendations_router._dismissed_ids
    try:
        recommendations_router._last_recommendations = []
        recommendations_router._applied_recommendations = {}
        recommendations_router._dismissed_ids = set()
        client = TestClient(app)
        # No valid bearer should be able to inspect/mutate these endpoints.
        response = client.post("/api/v1/recommendations/not-owned-by-user/apply")
        assert response.status_code == 401
    finally:
        recommendations_router._last_recommendations = previous_recs
        recommendations_router._applied_recommendations = previous_applied
        recommendations_router._dismissed_ids = previous_dismissed


def test_invalid_bearer_token_is_rejected_when_auth_is_configured(monkeypatch):
    from app import auth
    from app.config import Settings

    monkeypatch.setattr(
        auth,
        "get_settings",
        lambda: Settings(supabase_url="https://project-ref.supabase.co"),
    )
    response = TestClient(app).get(
        "/api/v1/auth/session",
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert response.status_code == 401


def test_demo_apply_path_does_not_mark_recommendation_applied(monkeypatch):
    from app.config import Settings
    from app.routers import recommendations as rec_router
    from app.schemas import ApplyResponse, RecommendationItem

    recommendation = RecommendationItem(
        id="demo-rec",
        category="cost",
        priority="medium",
        title="Demo recommendation",
        description="Synthetic demo recommendation",
        impact_summary="Estimated only",
        estimated_monthly_savings_usd=10.0,
        estimated_carbon_reduction_pct=2.0,
        effort="low",
        action="resize",
        evidence=[],
        confidence=0.5,
    )
    monkeypatch.setattr(rec_router, "settings", Settings(demo_mode=True))
    monkeypatch.setattr(rec_router, "_last_recommendations", [recommendation])
    from app.integrations.cloud_actions import CloudActionDispatcher
    monkeypatch.setattr(
        CloudActionDispatcher,
        "execute_recommendation",
        lambda **kwargs: ApplyResponse(
            recommendation_id="demo-rec",
            title="Demo recommendation",
            status="simulated",
            message="No live action taken",
            dry_run=True,
            estimated_monthly_savings_usd=10.0,
            estimated_carbon_reduction_pct=2.0,
            steps_taken=["Simulation only"],
            applied_at=None,
        ),
        raising=False,
    )
    rec_router._applied_recommendations.clear()

    result = rec_router.apply_recommendation("demo-rec", None)
    assert result.status == "simulated"
    assert recommendation.status != "applied"
    assert "demo-rec" not in rec_router._applied_recommendations


def test_loopback_cors_origins_are_only_defaulted_outside_production():
    production = Settings(
        app_env="production",
        allowed_origins="https://app.example.com",
    )
    development = Settings(
        app_env="development",
        allowed_origins="https://app.example.com",
    )
    assert "http://localhost:5173" not in production.get_allowed_origins()
    assert "http://127.0.0.1:3000" not in production.get_allowed_origins()
    assert "http://localhost:5173" in development.get_allowed_origins()
    assert "http://127.0.0.1:3000" in development.get_allowed_origins()
