"""Regression checks for the explicit-origin CORS policy."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_cors_allows_configured_origin_and_rejects_unknown_origin():
    allowed = client.options(
        "/api/v1/telemetry/live",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"

    rejected = client.options(
        "/api/v1/telemetry/live",
        headers={
            "Origin": "https://attacker.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers


def test_cors_allows_local_network_origins():
    # LAN IP on Vite default port
    res_lan = client.options(
        "/api/v1/telemetry/live",
        headers={
            "Origin": "http://192.168.1.50:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res_lan.status_code == 200
    assert res_lan.headers["access-control-allow-origin"] == "http://192.168.1.50:5173"

    # Private network 10.x.x.x
    res_private = client.options(
        "/api/v1/telemetry/live",
        headers={
            "Origin": "http://10.0.0.12:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res_private.status_code == 200
    assert res_private.headers["access-control-allow-origin"] == "http://10.0.0.12:3000"


def test_cors_allows_vercel_preview_domains():
    res_vercel = client.options(
        "/api/v1/telemetry/live",
        headers={
            "Origin": "https://greenmind-ai-preview-pr12.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res_vercel.status_code == 200
    assert res_vercel.headers["access-control-allow-origin"] == "https://greenmind-ai-preview-pr12.vercel.app"


def test_cors_headers_preserved_on_http_exceptions():
    from app import auth
    override = app.dependency_overrides.pop(auth.require_authenticated_user, None)
    try:
        res = client.get(
            "/api/v1/auth/session",
            headers={
                "Origin": "https://green-mind-ai-ten.vercel.app",
                "Authorization": "Bearer invalid_test_token",
            },
        )
        assert res.status_code == 401
        assert res.headers["access-control-allow-origin"] == "https://green-mind-ai-ten.vercel.app"
        assert res.headers["access-control-allow-credentials"] == "true"
        assert "detail" in res.json()
    finally:
        if override is not None:
            app.dependency_overrides[auth.require_authenticated_user] = override


def test_cors_headers_preserved_on_unhandled_exceptions(monkeypatch):
    from app.routers import telemetry

    def exploding_route(*_args, **_kwargs):
        raise RuntimeError("Simulated crash")

    monkeypatch.setattr(telemetry, "_generate_live_metrics", exploding_route)
    safe_client = TestClient(app, raise_server_exceptions=False)
    res = safe_client.get(
        "/api/v1/telemetry/live",
        headers={
            "Origin": "https://green-mind-ai-ten.vercel.app",
            "Authorization": "Bearer dev-test",
        },
    )
    # Even on internal crash, CORS headers must be present so browser doesn't report opaque Network Error
    assert res.status_code == 500
    assert res.headers["access-control-allow-origin"] == "https://green-mind-ai-ten.vercel.app"
    assert res.headers["access-control-allow-credentials"] == "true"



