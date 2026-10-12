"""Security regression tests for unauthenticated access and exact CORS allowlists."""
from fastapi.testclient import TestClient
from starlette.middleware.cors import CORSMiddleware

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


def test_app_cors_middleware_has_no_origin_regex():
    cors = next(
        middleware.cls
        for middleware in app.user_middleware
        if middleware.cls is CORSMiddleware
    )
    assert cors is CORSMiddleware
    # Middleware is built with explicit origins; broad regexes must not be configured.
    cors_options = next(
        middleware.options
        for middleware in app.user_middleware
        if middleware.cls is CORSMiddleware
    )
    assert "allow_origin_regex" not in cors_options
    assert cors_options["allow_origins"] == settings.get_allowed_origins()
