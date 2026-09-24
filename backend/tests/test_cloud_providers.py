"""
Unit tests for Cloud Provider Authentication, Connection Testing, and 4-Tier Status Model (Phase 2).
Covers:
- 4-Tier connection state model (CONFIGURED, AUTHENTICATED, REACHABLE, OPERATIONAL)
- get_account_info(), get_regions(), validate_credentials()
- AWS STS / EC2 / CloudWatch authentication (success and failure modes)
- Azure AD OAuth2 / ARM subscription authentication (success and failure modes)
- GCP Service Account / Monitoring authentication (success and failure modes)
- Data truth assertion: invalid credentials return explicit ERROR, never DEMO or fake LIVE
- Settings router endpoints for account-info, regions, and connection testing
"""

import os
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient

from app.cloud import get_provider, reset_all_providers
from app.cloud.aws_provider import AWSCloudProvider
from app.cloud.azure_provider import AzureCloudProvider
from app.cloud.gcp_provider import GCPCloudProvider
from app.main import app

client = TestClient(app)


def setup_function():
    reset_all_providers()


# ── AWS PROVIDER TESTS ────────────────────────────────────────────────────────

def test_aws_provider_demo_status_and_methods():
    """Verify AWS provider exposes 4-tier model and normalized methods in unconfigured state."""
    provider = AWSCloudProvider()
    status = provider.get_status()

    # 4-tier status checks
    assert "credentials_status" in status
    assert "authentication_status" in status
    assert "api_reachability" in status
    assert "telemetry_status" in status
    assert status["credentials_status"] == "NOT_CONFIGURED"
    assert status["authentication_status"] == "NOT_CONFIGURED"
    assert status["api_reachability"] == "NOT_CONFIGURED"
    assert status["telemetry_status"] == "DEMO"
    assert status["mode"] == "DEMO"
    assert status["status"] == "demo"

    # Normalized methods
    acct = provider.get_account_info()
    assert acct["provider"] == "aws"
    assert "account_id" in acct
    assert "arn" in acct
    assert acct["mode"] == "DEMO"

    regions = provider.get_regions()
    assert len(regions) >= 5
    assert any(r["id"] == "us-east-1" for r in regions)
    assert any(r["id"] == "ap-south-1" for r in regions)


def test_aws_provider_live_authentication_success():
    """Verify AWS provider handles successful STS + CloudWatch authentication in LIVE mode."""
    with patch("boto3.Session") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        # Mock STS
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            "Account": "998877665544",
            "Arn": "arn:aws:iam::998877665544:user/greenmind-admin",
            "UserId": "AIDAIEXAMPLE",
        }

        # Mock EC2
        mock_ec2 = MagicMock()
        mock_ec2.describe_regions.return_value = {
            "Regions": [{"RegionName": "us-east-1"}, {"RegionName": "ap-south-1"}]
        }

        # Mock CloudWatch
        mock_cw = MagicMock()
        mock_cw.list_metrics.return_value = {"Metrics": []}

        def mock_client(service_name, **kwargs):
            if service_name == "sts":
                return mock_sts
            elif service_name == "ec2":
                return mock_ec2
            elif service_name == "cloudwatch":
                return mock_cw
            return MagicMock()

        mock_session.client.side_effect = mock_client

        provider = AWSCloudProvider()
        res = provider.test_connection(credentials={
            "aws_access_key_id": "AKIA_MOCK_TEST_KEY",
            "aws_secret_access_key": "MOCK_SECRET_KEY",
            "aws_default_region": "us-east-1",
        })

        assert res["success"] is True
        assert res["status"] == "connected"
        assert res["mode"] == "LIVE"
        assert res["credentials_status"] == "CONFIGURED"
        assert res["authentication_status"] == "SUCCESS"
        assert res["api_reachability"] == "REACHABLE"
        assert res["telemetry_status"] == "OPERATIONAL"
        assert res["account_info"]["account_id"] == "998877665544"
        assert provider.is_live is True


def test_aws_provider_authentication_failure():
    """Verify invalid AWS credentials return explicit ERROR status without falling back to DEMO."""
    with patch("boto3.Session") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        mock_sts = MagicMock()
        error_response = {
            "Error": {
                "Code": "InvalidClientTokenId",
                "Message": "The security token included in the request is invalid.",
            }
        }
        mock_sts.get_caller_identity.side_effect = ClientError(error_response, "GetCallerIdentity")
        mock_session.client.return_value = mock_sts

        provider = AWSCloudProvider()
        res = provider.test_connection(credentials={
            "aws_access_key_id": "AKIA_INVALID_TEST_KEY",
            "aws_secret_access_key": "INVALID_SECRET",
            "aws_default_region": "us-east-1",
        })

        assert res["success"] is False
        assert res["status"] == "authentication_failed"
        assert res["mode"] == "ERROR"
        assert res["credentials_status"] == "CONFIGURED"
        assert res["authentication_status"] == "FAILED"
        assert res["api_reachability"] == "UNREACHABLE"
        assert res["telemetry_status"] == "ERROR"
        assert "InvalidClientTokenId" in res["message"]
        assert provider.is_live is False


# ── AZURE PROVIDER TESTS ──────────────────────────────────────────────────────

def test_azure_provider_demo_status_and_methods():
    """Verify Azure provider exposes 4-tier model and normalized methods."""
    provider = AzureCloudProvider()
    status = provider.get_status()

    assert status["credentials_status"] == "NOT_CONFIGURED"
    assert status["authentication_status"] == "NOT_CONFIGURED"
    assert status["api_reachability"] == "NOT_CONFIGURED"
    assert status["telemetry_status"] == "DEMO"
    assert status["mode"] == "DEMO"

    acct = provider.get_account_info()
    assert acct["provider"] == "azure"
    assert "subscription_id" in acct
    assert acct["mode"] == "DEMO"

    regions = provider.get_regions()
    assert len(regions) >= 5
    assert any(r["id"] == "eastus" for r in regions)
    assert any(r["id"] == "centralindia" for r in regions)


def test_azure_provider_live_authentication_success():
    """Verify Azure provider handles successful OAuth2 token + ARM subscription call."""
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client

        token_resp = MagicMock()
        token_resp.status_code = 200
        token_resp.json.return_value = {"access_token": "mock-azure-token-xyz", "expires_in": 3600}

        sub_resp = MagicMock()
        sub_resp.status_code = 200
        sub_resp.json.return_value = {
            "id": "/subscriptions/sub-12345",
            "subscriptionId": "sub-12345",
            "displayName": "Production Enterprise Subscription",
            "state": "Enabled",
        }

        mock_client.post.return_value = token_resp
        mock_client.get.return_value = sub_resp

        provider = AzureCloudProvider()
        res = provider.test_connection(credentials={
            "azure_subscription_id": "sub-12345",
            "azure_tenant_id": "tenant-67890",
            "azure_client_id": "client-abcde",
            "azure_client_secret": "secret-xyz",
        })

        assert res["success"] is True
        assert res["status"] == "connected"
        assert res["mode"] == "LIVE"
        assert res["credentials_status"] == "CONFIGURED"
        assert res["authentication_status"] == "SUCCESS"
        assert res["api_reachability"] == "REACHABLE"
        assert res["telemetry_status"] == "OPERATIONAL"
        assert "Production Enterprise Subscription" in res["message"]
        assert provider.is_live is True


def test_azure_provider_authentication_failure():
    """Verify invalid Azure client credentials return explicit ERROR."""
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client

        token_resp = MagicMock()
        token_resp.status_code = 401
        token_resp.json.return_value = {
            "error": "invalid_client",
            "error_description": "Invalid client secret provided.",
        }
        mock_client.post.return_value = token_resp

        provider = AzureCloudProvider()
        res = provider.test_connection(credentials={
            "azure_subscription_id": "sub-12345",
            "azure_tenant_id": "tenant-67890",
            "azure_client_id": "client-abcde",
            "azure_client_secret": "invalid-secret",
        })

        assert res["success"] is False
        assert res["status"] == "authentication_failed"
        assert res["mode"] == "ERROR"
        assert res["credentials_status"] == "CONFIGURED"
        assert res["authentication_status"] == "FAILED"
        assert res["api_reachability"] == "UNREACHABLE"
        assert res["telemetry_status"] == "ERROR"
        assert provider.is_live is False


# ── GCP PROVIDER TESTS ────────────────────────────────────────────────────────

def test_gcp_provider_demo_status_and_methods():
    """Verify GCP provider exposes 4-tier model and normalized methods."""
    provider = GCPCloudProvider()
    status = provider.get_status()

    assert status["credentials_status"] == "NOT_CONFIGURED"
    assert status["authentication_status"] == "NOT_CONFIGURED"
    assert status["api_reachability"] == "NOT_CONFIGURED"
    assert status["telemetry_status"] == "DEMO"
    assert status["mode"] == "DEMO"

    acct = provider.get_account_info()
    assert acct["provider"] == "gcp"
    assert "project_id" in acct
    assert acct["mode"] == "DEMO"

    regions = provider.get_regions()
    assert len(regions) >= 5
    assert any(r["id"] == "us-central1" for r in regions)
    assert any(r["id"] == "asia-south1" for r in regions)


def test_gcp_provider_live_authentication_success():
    """Verify GCP provider handles successful token + Cloud Monitoring API reachability."""
    with patch.object(GCPCloudProvider, "_get_access_token", return_value="mock-gcp-token"):
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client

            monitoring_resp = MagicMock()
            monitoring_resp.status_code = 200
            monitoring_resp.json.return_value = {"metricDescriptors": [{"name": "mock-descriptor"}]}
            mock_client.get.return_value = monitoring_resp

            provider = GCPCloudProvider()
            res = provider.test_connection(credentials={
                "gcp_project_id": "greenmind-prod-project",
                "gcp_service_account_json": '{"type": "service_account", "project_id": "greenmind-prod-project", "client_email": "sa@greenmind.iam.gserviceaccount.com"}',
            })

            assert res["success"] is True
            assert res["status"] == "connected"
            assert res["mode"] == "LIVE"
            assert res["credentials_status"] == "CONFIGURED"
            assert res["authentication_status"] == "SUCCESS"
            assert res["api_reachability"] == "REACHABLE"
            assert res["telemetry_status"] == "OPERATIONAL"
            assert "greenmind-prod-project" in res["message"]
            assert provider.is_live is True


def test_gcp_provider_authentication_failure():
    """Verify invalid GCP service account returns explicit ERROR."""
    with patch.object(GCPCloudProvider, "_get_access_token", return_value=None):
        provider = GCPCloudProvider()
        res = provider.test_connection(credentials={
            "gcp_project_id": "invalid-project",
            "gcp_service_account_json": '{"invalid": "data"}',
        })

        assert res["success"] is False
        assert res["status"] == "authentication_failed"
        assert res["mode"] == "ERROR"
        assert res["credentials_status"] == "CONFIGURED"
        assert res["authentication_status"] == "FAILED"
        assert res["api_reachability"] == "UNREACHABLE"
        assert res["telemetry_status"] == "ERROR"
        assert provider.is_live is False


# ── SETTINGS ROUTER ENDPOINTS TESTS ──────────────────────────────────────────

def test_settings_router_status_4tier():
    """Verify /api/v1/settings/status endpoint exposes 4-tier model for all providers."""
    resp = client.get("/api/v1/settings/status")
    assert resp.status_code == 200
    data = resp.json()

    assert "providers" in data
    assert "aws" in data["providers"]
    assert "azure" in data["providers"]
    assert "gcp" in data["providers"]

    for prov in ["aws", "azure", "gcp"]:
        p_data = data["providers"][prov]
        assert "credentials_status" in p_data
        assert "authentication_status" in p_data
        assert "api_reachability" in p_data
        assert "telemetry_status" in p_data
        assert "status" in p_data
        assert "mode" in p_data


def test_settings_account_info_and_regions():
    """Verify /api/v1/settings/account-info and /regions endpoints."""
    # Account info
    resp_acct = client.get("/api/v1/settings/account-info/aws")
    assert resp_acct.status_code == 200
    acct = resp_acct.json()
    assert acct["provider"] == "aws"
    assert "account_id" in acct

    # Regions
    resp_reg = client.get("/api/v1/settings/regions/aws")
    assert resp_reg.status_code == 200
    regions = resp_reg.json()
    assert isinstance(regions, list)
    assert len(regions) >= 5

    # Unsupported provider
    resp_err = client.get("/api/v1/settings/account-info/unsupported")
    assert resp_err.status_code == 400


def test_settings_validate_credentials():
    """Verify /api/v1/settings/validate-credentials tests connection without state side-effects."""
    payload = {
        "provider": "aws",
        "credentials": {
            "aws_access_key_id": "AKIA_FAKE_VALIDATION_KEY",
            "aws_secret_access_key": "fake_secret",
            "aws_default_region": "us-east-1",
        },
    }
    resp = client.post("/api/v1/settings/validate-credentials", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "aws"
    assert data["success"] is False
    assert data["status"] == "authentication_failed"
    assert data["mode"] == "ERROR"
