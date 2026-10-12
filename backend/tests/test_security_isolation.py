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
