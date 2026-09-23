"""Tests for Settings & Multi-Cloud Provider Management API.

Verifies:
- Safe configuration retrieval (zero secrets leaked)
- Connection test endpoints for AWS, Azure, GCP
- Configure & Disconnect endpoints
- Error handling (invalid credentials never cause 500 crashes)
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_settings_status_zero_secret_leakage():
    """Verify settings status endpoint returns sanitized metadata and no secrets."""
    res = client.get("/api/v1/settings/status")
    assert res.status_code == 200
    data = res.json()

    assert "system_mode" in data
    assert "providers" in data
    assert "llm" in data
    assert "database" in data

    providers = data["providers"]
    for p in ["aws", "azure", "gcp"]:
        assert p in providers
        assert "mode" in providers[p]
        assert "status" in providers[p]
        assert "message" in providers[p]

        # Explicitly verify NO raw secret values exist
        raw_text = str(providers[p]).lower()
        assert "wjalrxfn" not in raw_text
        assert "sk-" not in raw_text
        assert "aizasy" not in raw_text


def test_settings_test_connection_unknown_provider():
    """Test connecting to unsupported provider returns 400."""
    res = client.post("/api/v1/settings/test-connection", json={"provider": "oracle_cloud"})
    assert res.status_code == 400
    assert "Unsupported provider" in res.json()["detail"]


def test_settings_test_connection_aws_invalid_creds():
    """Test AWS connection with invalid dummy credentials returns auth_failed cleanly (no 500)."""
    res = client.post(
        "/api/v1/settings/test-connection",
        json={
            "provider": "aws",
            "credentials": {
                "aws_access_key_id": "AKIAINVALIDTESTKEY00",
                "aws_secret_access_key": "invalid_secret_for_testing_1234567890",
                "aws_default_region": "us-east-1",
            },
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] == "aws"
    assert data["status"] in ["authentication_failed", "auth_failed", "not_configured", "service_unavailable"]
    assert "message" in data


def test_settings_test_connection_azure_invalid_creds():
    """Test Azure connection with invalid dummy credentials returns auth_failed cleanly (no 500)."""
    res = client.post(
        "/api/v1/settings/test-connection",
        json={
            "provider": "azure",
            "credentials": {
                "azure_subscription_id": "00000000-0000-0000-0000-000000000000",
                "azure_tenant_id": "00000000-0000-0000-0000-000000000000",
                "azure_client_id": "00000000-0000-0000-0000-000000000000",
                "azure_client_secret": "invalid_secret_value",
            },
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] == "azure"
    assert data["status"] in ["authentication_failed", "auth_failed", "not_configured", "service_unavailable"]
    assert "message" in data


def test_settings_test_connection_gcp_invalid_creds():
    """Test GCP connection with invalid dummy credentials returns auth_failed cleanly (no 500)."""
    res = client.post(
        "/api/v1/settings/test-connection",
        json={
            "provider": "gcp",
            "credentials": {
                "gcp_project_id": "invalid-dummy-project",
                "gcp_service_account_json": '{"type": "service_account", "project_id": "invalid"}',
            },
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] == "gcp"
    assert data["status"] in ["authentication_failed", "auth_failed", "not_configured", "service_unavailable"]
    assert "message" in data


def test_settings_configure_and_disconnect():
    """Test configuring a provider and disconnecting back to demo."""
    # Configure dummy AWS
    res = client.post(
        "/api/v1/settings/configure",
        json={
            "provider": "aws",
            "credentials": {
                "aws_access_key_id": "AKIAEXAMPLEKEY",
                "aws_secret_access_key": "example_secret",
                "aws_default_region": "us-east-1",
            },
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["provider"] == "aws"

    # Now disconnect
    disc = client.post(
        "/api/v1/settings/disconnect",
        json={"provider": "aws"},
    )
    assert disc.status_code == 200
    disc_data = disc.json()
    assert disc_data["status"] == "disconnected"
    assert "Reset to Demo" in disc_data["message"]


def test_dual_path_registration():
    """Verify endpoints are accessible under both /api/v1/ and root."""
    h1 = client.get("/health")
    h2 = client.get("/api/v1/health")
    assert h1.status_code == 200
    assert h2.status_code == 200
    assert h1.json()["status"] == h2.json()["status"]

    p1 = client.get("/cloud/providers")
    p2 = client.get("/api/v1/cloud/providers")
    assert p1.status_code == 200
    assert p2.status_code == 200
    assert len(p1.json()["providers"]) == len(p2.json()["providers"])
