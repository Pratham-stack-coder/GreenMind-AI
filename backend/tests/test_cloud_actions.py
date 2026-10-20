"""
Comprehensive tests for real cloud action remediation, verification, and rollback guardrails.
"""

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.cloud import update_provider_credentials, clear_provider_credentials
from app.config import get_settings
from app.integrations.cloud_actions import CloudActionDispatcher, CloudActionFailure
from app.main import app
from app.schemas import RecommendationItem

client = TestClient(app)


def _instance(**overrides):
    instance = {
        "InstanceId": "i-0123456789abcdef0",
        "State": {"Name": "running"},
        "InstanceType": "m5.large",
        "RootDeviceType": "ebs",
        "BlockDeviceMappings": [{"DeviceName": "/dev/xvda", "Ebs": {"VolumeId": "vol-123"}}],
        "Architecture": "x86_64",
        "VirtualizationType": "hvm",
    }
    instance.update(overrides)
    return instance


def _boto3_mock(ec2):
    session = MagicMock()
    session.client.return_value = ec2
    return SimpleNamespace(Session=MagicMock(return_value=session))


def test_dry_run_preview_never_mutates_cloud(monkeypatch):
    ec2 = MagicMock()
    monkeypatch.setitem(sys.modules, "boto3", _boto3_mock(ec2))

    rec = RecommendationItem(
        id="rec-cost-idle",
        category="cost",
        priority="high",
        title="Stop Idle EC2 Instance",
        description="Instance has < 5% CPU for 48 hours",
        impact_summary="Save $70/mo",
        action="terminate_idle",
        estimated_monthly_savings_usd=70.0,
    )

    import asyncio
    res = asyncio.run(CloudActionDispatcher.execute_recommendation(
        rec=rec,
        dry_run=True,
        confirm_live=False,
        resource_id="i-0123456789abcdef0",
    ))

    assert res.dry_run is True
    assert res.status == "simulated"
    assert res.verified is False
    ec2.stop_instances.assert_not_called()
    ec2.terminate_instances.assert_not_called()


def test_live_mutation_rejected_without_explicit_confirmation():
    rec = RecommendationItem(
        id="rec-cost-idle",
        category="cost",
        priority="high",
        title="Stop Idle EC2 Instance",
        description="Instance has < 5% CPU",
        impact_summary="Save $70/mo",
        action="terminate_idle",
    )

    import asyncio
    with pytest.raises(HTTPException) as exc:
        asyncio.run(CloudActionDispatcher.execute_recommendation(
            rec=rec,
            dry_run=False,
            confirm_live=False,
            resource_id="i-0123456789abcdef0",
        ))

    assert exc.value.status_code == 501
    assert "Live cloud remediation is not implemented for unconfirmed actions" in exc.value.detail


def test_live_mutation_rejected_for_unsupported_provider():
    rec = RecommendationItem(
        id="rec-azure-idle",
        category="cost",
        priority="high",
        title="Idle Azure VM",
        description="VM is idle",
        impact_summary="Save $50/mo",
        action="terminate_idle",
    )

    import asyncio
    with pytest.raises(HTTPException) as exc:
        asyncio.run(CloudActionDispatcher.execute_recommendation(
            rec=rec,
            dry_run=False,
            confirm_live=True,
            provider="azure",
            resource_id="vm-prod-01",
        ))

    assert exc.value.status_code == 501
    assert "azure" in exc.value.detail.lower()


def test_live_mutation_rejected_for_unsupported_action():
    rec = RecommendationItem(
        id="rec-scale-out",
        category="performance",
        priority="high",
        title="Scale Out Cluster",
        description="CPU saturation",
        impact_summary="Add capacity",
        action="scale_out",
    )

    import asyncio
    with pytest.raises(HTTPException) as exc:
        asyncio.run(CloudActionDispatcher.execute_recommendation(
            rec=rec,
            dry_run=False,
            confirm_live=True,
            provider="aws",
            resource_id="i-0123456789abcdef0",
        ))

    assert exc.value.status_code == 501
    assert "scale_out" in exc.value.detail


def test_live_mutation_rejected_without_resource_id(monkeypatch):
    from app.auth import _current_user_id
    token = _current_user_id.set("test-user-id")
    try:
        settings = get_settings()
        monkeypatch.setattr(settings, "demo_mode", False)
        update_provider_credentials("aws", {"aws_access_key_id": "test", "aws_secret_access_key": "test"})

        rec = RecommendationItem(
            id="rec-idle",
            category="cost",
            priority="high",
            title="Stop Idle EC2 Instance",
            description="Idle instance",
            impact_summary="Save $50/mo",
            action="terminate_idle",
        )

        import asyncio
        with pytest.raises(HTTPException) as exc:
            asyncio.run(CloudActionDispatcher.execute_recommendation(
                rec=rec,
                dry_run=False,
                confirm_live=True,
                provider="aws",
                resource_id="",
            ))

        assert exc.value.status_code == 400
        assert "resource_id" in exc.value.detail.lower()
    finally:
        _current_user_id.reset(token)


def test_spot_instance_rejected_before_mutation(monkeypatch):
    ec2 = MagicMock()
    ec2.describe_instances.return_value = {
        "Reservations": [{"Instances": [_instance(InstanceLifecycle="spot")]}]
    }
    monkeypatch.setitem(sys.modules, "boto3", _boto3_mock(ec2))

    with pytest.raises(HTTPException) as exc:
        CloudActionDispatcher._apply_aws_ec2(
            credentials={"aws_access_key_id": "test", "aws_secret_access_key": "test"},
            selected_region="us-east",
            resource_id="i-0123456789abcdef0",
            action="terminate_idle",
            target_instance_type=None,
        )

    assert exc.value.status_code == 422
    assert "Spot instances are excluded" in exc.value.detail
    ec2.stop_instances.assert_not_called()
    ec2.terminate_instances.assert_not_called()


def test_instance_store_rejected_before_mutation(monkeypatch):
    ec2 = MagicMock()
    ec2.describe_instances.return_value = {
        "Reservations": [{"Instances": [_instance(RootDeviceType="instance-store")]}]
    }
    monkeypatch.setitem(sys.modules, "boto3", _boto3_mock(ec2))

    with pytest.raises(HTTPException) as exc:
        CloudActionDispatcher._apply_aws_ec2(
            credentials={"aws_access_key_id": "test", "aws_secret_access_key": "test"},
            selected_region="us-east",
            resource_id="i-0123456789abcdef0",
            action="terminate_idle",
            target_instance_type=None,
        )

    assert exc.value.status_code == 422
    assert "instance-store" in exc.value.detail.lower()
    ec2.stop_instances.assert_not_called()


def test_idle_instance_safe_stop_and_verified(monkeypatch):
    ec2 = MagicMock()
    # First describe: running. Second describe (verification): stopped.
    ec2.describe_instances.side_effect = [
        {"Reservations": [{"Instances": [_instance(State={"Name": "running"})]}]},
        {"Reservations": [{"Instances": [_instance(State={"Name": "stopped"})]}]},
    ]
    ec2.get_waiter.return_value = MagicMock()
    monkeypatch.setitem(sys.modules, "boto3", _boto3_mock(ec2))

    result = CloudActionDispatcher._apply_aws_ec2(
        credentials={"aws_access_key_id": "test", "aws_secret_access_key": "test"},
        selected_region="us-east",
        resource_id="i-0123456789abcdef0",
        action="terminate_idle",
        target_instance_type=None,
    )

    ec2.stop_instances.assert_called_once_with(InstanceIds=["i-0123456789abcdef0"])
    ec2.terminate_instances.assert_not_called()
    assert result["current_state"] == "stopped"
    assert "verified instance i-0123456789abcdef0 state is 'stopped'" in " ".join(result["steps"]).lower()


def test_resize_downsizing_validation_and_verified_execution(monkeypatch):
    ec2 = MagicMock()
    # Pre-check describe, post-check describe
    ec2.describe_instances.side_effect = [
        {"Reservations": [{"Instances": [_instance(InstanceType="m5.large", State={"Name": "running"})]}]},
        {"Reservations": [{"Instances": [_instance(InstanceType="t3.medium", State={"Name": "running"})]}]},
    ]
    ec2.describe_instance_types.return_value = {
        "InstanceTypes": [
            {
                "InstanceType": "m5.large",
                "VCpuInfo": {"DefaultVCpus": 2},
                "MemoryInfo": {"SizeInMiB": 8192},
                "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
                "SupportedVirtualizationTypes": ["hvm"],
            },
            {
                "InstanceType": "t3.medium",
                "VCpuInfo": {"DefaultVCpus": 2},
                "MemoryInfo": {"SizeInMiB": 4096},
                "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
                "SupportedVirtualizationTypes": ["hvm"],
            },
        ]
    }
    ec2.get_waiter.return_value = MagicMock()
    monkeypatch.setitem(sys.modules, "boto3", _boto3_mock(ec2))

    result = CloudActionDispatcher._apply_aws_ec2(
        credentials={"aws_access_key_id": "test", "aws_secret_access_key": "test"},
        selected_region="us-east",
        resource_id="i-0123456789abcdef0",
        action="right_size_down",
        target_instance_type="t3.medium",
    )

    ec2.stop_instances.assert_called_once_with(InstanceIds=["i-0123456789abcdef0"])
    ec2.modify_instance_attribute.assert_called_once_with(
        InstanceId="i-0123456789abcdef0",
        InstanceType={"Value": "t3.medium"},
    )
    ec2.start_instances.assert_called_once_with(InstanceIds=["i-0123456789abcdef0"])
    assert result["current_state"] == "t3.medium"
    assert "verified instance i-0123456789abcdef0 is running with new type t3.medium" in " ".join(result["steps"]).lower()


def test_resize_rejects_upsize(monkeypatch):
    ec2 = MagicMock()
    ec2.describe_instances.return_value = {
        "Reservations": [{"Instances": [_instance(InstanceType="m5.large")]}]
    }
    ec2.describe_instance_types.return_value = {
        "InstanceTypes": [
            {
                "InstanceType": "m5.large",
                "VCpuInfo": {"DefaultVCpus": 2},
                "MemoryInfo": {"SizeInMiB": 8192},
                "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
                "SupportedVirtualizationTypes": ["hvm"],
            },
            {
                "InstanceType": "m5.2xlarge",
                "VCpuInfo": {"DefaultVCpus": 8},
                "MemoryInfo": {"SizeInMiB": 32768},
                "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
                "SupportedVirtualizationTypes": ["hvm"],
            },
        ]
    }
    monkeypatch.setitem(sys.modules, "boto3", _boto3_mock(ec2))

    with pytest.raises(HTTPException) as exc:
        CloudActionDispatcher._apply_aws_ec2(
            credentials={"aws_access_key_id": "test", "aws_secret_access_key": "test"},
            selected_region="us-east",
            resource_id="i-0123456789abcdef0",
            action="right_size_down",
            target_instance_type="m5.2xlarge",
        )

    assert exc.value.status_code == 422
    assert "no more vcpu or memory" in exc.value.detail.lower()
    ec2.stop_instances.assert_not_called()


def test_rollback_restarts_stopped_instance(monkeypatch):
    ec2 = MagicMock()
    ec2.get_waiter.return_value = MagicMock()
    monkeypatch.setitem(sys.modules, "boto3", _boto3_mock(ec2))

    rec = RecommendationItem(
        id="rec-idle",
        category="cost",
        priority="high",
        title="Stop Idle EC2 Instance",
        description="Instance was stopped",
        impact_summary="Save $50/mo",
        action="terminate_idle",
    )

    import asyncio
    res = asyncio.run(CloudActionDispatcher.rollback_recommendation(
        rec=rec,
        resource_id="i-0123456789abcdef0",
        provider="aws",
        region="us-east",
    ))

    assert res.status == "rolled_back"
    assert res.verified is True
    assert res.current_state == "running"
    ec2.start_instances.assert_called_once_with(InstanceIds=["i-0123456789abcdef0"])
