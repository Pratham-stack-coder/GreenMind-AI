"""Safety tests for explicitly confirmed AWS EC2 remediation."""

import asyncio
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.integrations.cloud_actions import CloudActionDispatcher
from app.schemas import RecommendationItem


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


def test_idle_recommendation_stops_instance_without_terminating(monkeypatch):
    ec2 = MagicMock()
    ec2.describe_instances.return_value = {"Reservations": [{"Instances": [_instance()]}]}
    ec2.get_waiter.return_value = MagicMock()

    monkeypatch.setitem(sys.modules, "boto3", _boto3_mock(ec2))
    result = CloudActionDispatcher._apply_aws_ec2(
        {"aws_access_key_id": "test", "aws_secret_access_key": "test"},
        "us-east",
        "i-0123456789abcdef0",
        "terminate_idle",
        None,
    )

    ec2.stop_instances.assert_called_once_with(InstanceIds=["i-0123456789abcdef0"])
    ec2.terminate_instances.assert_not_called()
    assert "not terminated" in result["message"]



def test_resize_stops_modifies_and_restarts_only_after_validation(monkeypatch):
    ec2 = MagicMock()
    ec2.describe_instances.return_value = {"Reservations": [{"Instances": [_instance()]}]}
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
        {"aws_access_key_id": "test", "aws_secret_access_key": "test"},
        "us-east",
        "i-0123456789abcdef0",
        "right_size_down",
        "t3.medium",
    )

    ec2.stop_instances.assert_called_once_with(InstanceIds=["i-0123456789abcdef0"])
    ec2.modify_instance_attribute.assert_called_once_with(
        InstanceId="i-0123456789abcdef0",
        InstanceType={"Value": "t3.medium"},
    )
    ec2.start_instances.assert_called_once_with(InstanceIds=["i-0123456789abcdef0"])
    assert "confirmed the running state" in " ".join(result["steps"])


def test_resize_rejects_larger_instance_type_before_stopping(monkeypatch):
    ec2 = MagicMock()
    ec2.describe_instances.return_value = {"Reservations": [{"Instances": [_instance()]}]}
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
                "InstanceType": "m5.xlarge",
                "VCpuInfo": {"DefaultVCpus": 4},
                "MemoryInfo": {"SizeInMiB": 16384},
                "ProcessorInfo": {"SupportedArchitectures": ["x86_64"]},
                "SupportedVirtualizationTypes": ["hvm"],
            },
        ]
    }
    monkeypatch.setitem(sys.modules, "boto3", _boto3_mock(ec2))

    with pytest.raises(HTTPException) as exc:
        CloudActionDispatcher._apply_aws_ec2(
            {"aws_access_key_id": "test", "aws_secret_access_key": "test"},
            "us-east",
            "i-0123456789abcdef0",
            "right_size_down",
            "m5.xlarge",
        )

    assert exc.value.status_code == 422
    ec2.stop_instances.assert_not_called()
    ec2.modify_instance_attribute.assert_not_called()


def test_live_dispatch_requires_explicit_confirmation():
    recommendation = RecommendationItem(
        id="rec-1",
        category="cost",
        priority="medium",
        title="Idle instance",
        description="Instance is idle",
        impact_summary="Reduce spend",
        action="terminate_idle",
    )

    async def run():
        return await CloudActionDispatcher.execute_recommendation(
            recommendation,
            dry_run=False,
            provider="aws",
            region="us-east",
            confirm_live=False,
            resource_id="i-0123456789abcdef0",
        )

    with patch("app.integrations.cloud_actions.get_provider") as get_provider:
        with pytest.raises(HTTPException) as exc:
            asyncio.run(run())

    assert exc.value.status_code == 400
    get_provider.assert_not_called()


def test_spot_instance_rejected_without_cloud_mutation(monkeypatch):
    ec2 = MagicMock()
    ec2.describe_instances.return_value = {
        "Reservations": [{"Instances": [_instance(InstanceLifecycle="spot")]}]
    }
    monkeypatch.setitem(sys.modules, "boto3", _boto3_mock(ec2))

    with pytest.raises(HTTPException) as exc:
        CloudActionDispatcher._apply_aws_ec2(
            {"aws_access_key_id": "test", "aws_secret_access_key": "test"},
            "us-east",
            "i-0123456789abcdef0",
            "terminate_idle",
            None,
        )

    assert exc.value.status_code == 422
    ec2.stop_instances.assert_not_called()
    ec2.terminate_instances.assert_not_called()
