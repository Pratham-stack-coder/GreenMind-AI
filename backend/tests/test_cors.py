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
