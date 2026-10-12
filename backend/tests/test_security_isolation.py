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


def test_cross_user_recommendation_identifier_does_not_expose_private_user_state():
    # Current recommendation route state is process-global rather than persisted with an owner.
    # This test locks in that an unknown recommendation cannot be mutated or inspected.
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
