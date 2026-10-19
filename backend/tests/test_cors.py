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

