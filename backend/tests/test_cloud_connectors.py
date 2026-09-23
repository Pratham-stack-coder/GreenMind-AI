"""Unit and integration tests for multi-cloud telemetry connectors (AWS, Azure, GCP)."""

import pytest
from unittest.mock import MagicMock, patch
from app.cloud import get_provider
from app.cloud.aws_provider import AWSCloudProvider
from app.cloud.azure_provider import AzureCloudProvider
from app.cloud.gcp_provider import GCPCloudProvider


def test_provider_factory():
    """Verify provider factory returns appropriate provider instances."""
    aws = get_provider("aws")
    azure = get_provider("azure")
    gcp = get_provider("gcp")
    default = get_provider("unknown")

    assert isinstance(aws, AWSCloudProvider)
    assert isinstance(azure, AzureCloudProvider)
    assert isinstance(gcp, GCPCloudProvider)
    assert isinstance(default, AWSCloudProvider)


def test_aws_provider_demo_fallback():
    """Verify AWS provider returns structured metrics in demo mode."""
    provider = AWSCloudProvider()
    metrics = provider.get_metrics("us-east-1")
    assert metrics["provider"] == "aws"
    assert "cpu" in metrics
    assert "memory" in metrics
    assert "cost_usd_per_hour" in metrics
    assert "carbon_gco2_per_hour" in metrics
    assert metrics["source"] == "DEMO"

    resources = provider.get_resources("us-east-1")
    assert len(resources) > 0
    assert any(r.get("right_size_candidate") for r in resources)

    cost = provider.get_cost("us-east-1")
    assert cost["total_usd"] > 0
    assert len(cost["top_services"]) > 0

    health = provider.get_health("us-east-1")
    assert health["status"] == "HEALTHY"


def test_azure_provider_demo_fallback():
    """Verify Azure provider returns structured metrics in demo mode."""
    provider = AzureCloudProvider()
    metrics = provider.get_metrics("eastus")
    assert metrics["provider"] == "azure"
    assert "cpu" in metrics
    assert "memory" in metrics
    assert metrics["source"] == "DEMO"

    resources = provider.get_resources("eastus")
    assert len(resources) == 2
    assert resources[0]["provider"] == "azure"

    cost = provider.get_cost("eastus")
    assert cost["provider"] == "azure"
    assert cost["total_usd"] > 0

    health = provider.get_health("eastus")
    assert health["health_score"] >= 90


def test_gcp_provider_demo_fallback():
    """Verify GCP provider returns structured metrics in demo mode."""
    provider = GCPCloudProvider()
    metrics = provider.get_metrics("us-central1")
    assert metrics["provider"] == "gcp"
    assert "cpu" in metrics
    assert "network" in metrics
    assert metrics["source"] == "DEMO"

    resources = provider.get_resources("us-central1")
    assert len(resources) == 2
    assert resources[0]["provider"] == "gcp"

    cost = provider.get_cost("us-central1")
    assert cost["provider"] == "gcp"
    assert cost["total_usd"] > 0

    health = provider.get_health("us-central1")
    assert health["status"] == "HEALTHY"


def test_azure_provider_live_mock():
    """Verify Azure provider live metrics parsing with mocked HTTP responses."""
    provider = AzureCloudProvider()
    # Mock token acquisition and metrics response
    mock_token = "mock-azure-token-xyz"
    mock_metrics_data = {
        "value": [
            {
                "name": {"value": "Percentage CPU"},
                "timeseries": [
                    {"data": [{"average": 42.5}]}
                ],
            },
            {
                "name": {"value": "Network In Total"},
                "timeseries": [
                    {"data": [{"total": 15000000.0}]}
                ],
            },
            {
                "name": {"value": "Network Out Total"},
                "timeseries": [
                    {"data": [{"total": 25000000.0}]}
                ],
            },
        ]
    }

    with patch.object(provider, "_get_access_token", return_value=mock_token), \
         patch("httpx.Client.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_metrics_data
        mock_get.return_value = mock_resp

        parsed = provider.fetch_live_metrics("/subscriptions/sub-123/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm1")
        assert parsed is not None
        assert parsed["cpu"] == 42.5
        assert parsed["network_in"] == 15000000.0
        assert parsed["network_out"] == 25000000.0


def test_gcp_provider_live_mock():
    """Verify GCP provider live metrics parsing with mocked HTTP responses."""
    provider = GCPCloudProvider()
    provider.project_id = "test-greenmind-project"
    
    mock_gcp_data = {
        "timeSeries": [
            {
                "metric": {"type": "compute.googleapis.com/instance/cpu/utilization"},
                "points": [
                    {"value": {"doubleValue": 0.384}}
                ],
            }
        ]
    }

    with patch.object(provider, "_get_access_token", return_value="mock-gcp-token"), \
         patch("httpx.Client.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_gcp_data
        mock_get.return_value = mock_resp

        parsed = provider.fetch_live_metrics()
        assert parsed is not None
        assert parsed["cpu"] == 38.4
