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
    from app.auth import _current_user_id
    token = _current_user_id.set("test-user-id")
    try:
        settings = get_settings()
        monkeypatch.setattr(settings, "demo_mode", False)
        update_provider_credentials("aws", {"aws_access_key_id": "test", "aws_secret_access_key": "test"})

        ec2 = MagicMock()
        ec2.describe_instances.side_effect = [
            {"Reservations": [{"Instances": [_instance(State={"Name": "stopped"})]}]},
            {"Reservations": [{"Instances": [_instance(State={"Name": "running"})]}]},
        ]
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
        assert res.actual_operation == "restart_stopped_instance"
        ec2.start_instances.assert_called_once_with(InstanceIds=["i-0123456789abcdef0"])
    finally:
        _current_user_id.reset(token)


def test_rollback_rejected_in_demo_mode(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "demo_mode", True)
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
    with pytest.raises(HTTPException) as exc:
        asyncio.run(CloudActionDispatcher.rollback_recommendation(
            rec=rec,
            resource_id="i-0123456789abcdef0",
            provider="aws",
        ))
    assert exc.value.status_code == 422
    assert "DEMO_MODE" in exc.value.detail


def test_rollback_rejected_when_instance_already_running(monkeypatch):
    from app.auth import _current_user_id
    token = _current_user_id.set("test-user-id")
    try:
        settings = get_settings()
        monkeypatch.setattr(settings, "demo_mode", False)
        update_provider_credentials("aws", {"aws_access_key_id": "test", "aws_secret_access_key": "test"})

        ec2 = MagicMock()
        ec2.describe_instances.return_value = {
            "Reservations": [{"Instances": [_instance(State={"Name": "running"})]}]
        }
        monkeypatch.setitem(sys.modules, "boto3", _boto3_mock(ec2))

        rec = RecommendationItem(
            id="rec-idle",
            category="cost",
            priority="high",
            title="Stop Idle EC2 Instance",
            description="Instance was stopped",
            impact_summary="Save $50/mo",
            action="stop_idle",
        )

        import asyncio
        with pytest.raises(HTTPException) as exc:
            asyncio.run(CloudActionDispatcher.rollback_recommendation(
                rec=rec,
                resource_id="i-0123456789abcdef0",
                provider="aws",
            ))
        assert exc.value.status_code == 409
        assert "already in 'running' state" in exc.value.detail
        ec2.start_instances.assert_not_called()
    finally:
        _current_user_id.reset(token)


def test_rollback_rejected_when_instance_terminated(monkeypatch):
    from app.auth import _current_user_id
    token = _current_user_id.set("test-user-id")
    try:
        settings = get_settings()
        monkeypatch.setattr(settings, "demo_mode", False)
        update_provider_credentials("aws", {"aws_access_key_id": "test", "aws_secret_access_key": "test"})

        ec2 = MagicMock()
        ec2.describe_instances.return_value = {
            "Reservations": [{"Instances": [_instance(State={"Name": "terminated"})]}]
        }
        monkeypatch.setitem(sys.modules, "boto3", _boto3_mock(ec2))

        rec = RecommendationItem(
            id="rec-idle",
            category="cost",
            priority="high",
            title="Stop Idle EC2 Instance",
            description="Instance was stopped",
            impact_summary="Save $50/mo",
            action="stop_idle",
        )

        import asyncio
        with pytest.raises(HTTPException) as exc:
            asyncio.run(CloudActionDispatcher.rollback_recommendation(
                rec=rec,
                resource_id="i-0123456789abcdef0",
                provider="aws",
            ))
        assert exc.value.status_code == 409
        assert "terminated" in exc.value.detail
        ec2.start_instances.assert_not_called()
    finally:
        _current_user_id.reset(token)


def test_unverified_score_when_fresh_measurements_unavailable(monkeypatch):
    from app.auth import _current_user_id
    token = _current_user_id.set("test-user-id")
    try:
        settings = get_settings()
        monkeypatch.setattr(settings, "demo_mode", False)
        update_provider_credentials("aws", {"aws_access_key_id": "test", "aws_secret_access_key": "test"})

        ec2 = MagicMock()
        ec2.describe_instances.side_effect = [
            {"Reservations": [{"Instances": [_instance(State={"Name": "running"})]}]},
            {"Reservations": [{"Instances": [_instance(State={"Name": "stopped"})]}]},
        ]
        ec2.get_waiter.return_value = MagicMock()
        monkeypatch.setitem(sys.modules, "boto3", _boto3_mock(ec2))

        # Mock aws provider get_metrics to return demo fallback (not LIVE_AWS)
        mock_provider = MagicMock()
        mock_provider.is_configured = True
        mock_provider.get_metrics.return_value = {"source": "DEMO_FALLBACK"}
        monkeypatch.setattr("app.integrations.cloud_actions.get_provider", lambda p: mock_provider)

        rec = RecommendationItem(
            id="rec-idle",
            category="cost",
            priority="high",
            title="Stop Idle EC2 Instance",
            description="Instance has < 5% CPU",
            impact_summary="Save $50/mo",
            action="terminate_idle",
            estimated_monthly_savings_usd=50.0,
        )

        import asyncio
        res = asyncio.run(CloudActionDispatcher.execute_recommendation(
            rec=rec,
            dry_run=False,
            confirm_live=True,
            resource_id="i-0123456789abcdef0",
            provider="aws",
            projected_score=85,
            baseline_score=70,
        ))

        assert res.status == "applied"
        assert res.verified is True
        assert res.score_verified is False
        assert res.new_score is None
        assert res.projected_score == 85
        assert res.actual_operation == "stop_instance"
        assert any("score has not yet been verified" in step.lower() for step in res.steps_taken)
    finally:
        _current_user_id.reset(token)


def test_verified_score_recalculated_when_live_telemetry_available(monkeypatch):
    from app.auth import _current_user_id
    token = _current_user_id.set("test-user-id")
    try:
        settings = get_settings()
        monkeypatch.setattr(settings, "demo_mode", False)
        update_provider_credentials("aws", {"aws_access_key_id": "test", "aws_secret_access_key": "test"})

        ec2 = MagicMock()
        ec2.describe_instances.side_effect = [
            {"Reservations": [{"Instances": [_instance(State={"Name": "running"})]}]},
            {"Reservations": [{"Instances": [_instance(State={"Name": "stopped"})]}]},
        ]
        ec2.get_waiter.return_value = MagicMock()
        monkeypatch.setitem(sys.modules, "boto3", _boto3_mock(ec2))

        # Mock aws provider get_metrics to return LIVE_AWS telemetry
        mock_provider = MagicMock()
        mock_provider.is_live = True
        mock_provider.is_configured = True
        mock_provider.get_metrics.return_value = {
            "source": "LIVE_AWS",
            "timestamp": "2026-10-20T15:00:00Z",
            "region": "us-east-1",
            "cpu": 25.0,
            "memory": 40.0,
            "cost_usd_per_hour": 0.05,
        }
        monkeypatch.setattr("app.integrations.cloud_actions.get_provider", lambda p: mock_provider)

        rec = RecommendationItem(
            id="rec-idle",
            category="cost",
            priority="high",
            title="Stop Idle EC2 Instance",
            description="Instance has < 5% CPU",
            impact_summary="Save $50/mo",
            action="stop_idle",
            estimated_monthly_savings_usd=50.0,
        )

        import asyncio
        res = asyncio.run(CloudActionDispatcher.execute_recommendation(
            rec=rec,
            dry_run=False,
            confirm_live=True,
            resource_id="i-0123456789abcdef0",
            provider="aws",
            projected_score=85,
            baseline_score=70,
        ))

        assert res.status == "applied"
        assert res.score_verified is True
        assert res.new_score is not None
        assert res.actual_operation == "stop_instance"
        assert any("recalculated verified optimization score" in step.lower() for step in res.steps_taken)
    finally:
        _current_user_id.reset(token)


def test_action_name_differs_from_actual_operation(monkeypatch):
    from app.auth import _current_user_id
    token = _current_user_id.set("test-user-id")
    try:
        settings = get_settings()
        monkeypatch.setattr(settings, "demo_mode", False)
        update_provider_credentials("aws", {"aws_access_key_id": "test", "aws_secret_access_key": "test"})

        ec2 = MagicMock()
        ec2.describe_instances.side_effect = [
            {"Reservations": [{"Instances": [_instance(State={"Name": "running"})]}]},
            {"Reservations": [{"Instances": [_instance(State={"Name": "stopped"})]}]},
        ]
        ec2.get_waiter.return_value = MagicMock()
        monkeypatch.setitem(sys.modules, "boto3", _boto3_mock(ec2))

        rec = RecommendationItem(
            id="rec-idle-legacy",
            category="cost",
            priority="high",
            title="Stop Idle Instance",
            description="Legacy action naming test",
            impact_summary="Save $50/mo",
            action="terminate_idle",
        )

        import asyncio
        res = asyncio.run(CloudActionDispatcher.execute_recommendation(
            rec=rec,
            dry_run=False,
            confirm_live=True,
            resource_id="i-0123456789abcdef0",
            provider="aws",
        ))

        assert res.actual_operation == "stop_instance"
        assert "stopped, not terminated" in res.message.lower()
        assert "safely stopped" in res.message.lower()
        ec2.stop_instances.assert_called_once_with(InstanceIds=["i-0123456789abcdef0"])
        ec2.terminate_instances.assert_not_called()
    finally:
        _current_user_id.reset(token)


def test_audit_failure_blocks_reporting_success(monkeypatch):
    from app.auth import _current_user_id
    token = _current_user_id.set("test-user-id")
    try:
        settings = get_settings()
        monkeypatch.setattr(settings, "demo_mode", False)
        update_provider_credentials("aws", {"aws_access_key_id": "test", "aws_secret_access_key": "test"})

        ec2 = MagicMock()
        ec2.describe_instances.side_effect = [
            {"Reservations": [{"Instances": [_instance(State={"Name": "running"})]}]},
            {"Reservations": [{"Instances": [_instance(State={"Name": "stopped"})]}]},
        ]
        ec2.get_waiter.return_value = MagicMock()
        monkeypatch.setitem(sys.modules, "boto3", _boto3_mock(ec2))

        rec = RecommendationItem(
            id="rec-idle-audit",
            category="cost",
            priority="high",
            title="Stop Idle Instance",
            description="Testing audit failure propagation",
            impact_summary="Save $50/mo",
            action="stop_idle",
        )

        async def _failing_audit(*args, **kwargs):
            raise RuntimeError("Database disk full, audit logging failed")

        monkeypatch.setattr("app.integrations.cloud_actions.persist_audit_log", _failing_audit)

        import asyncio
        with pytest.raises(HTTPException) as exc:
            asyncio.run(CloudActionDispatcher.execute_recommendation(
                rec=rec,
                dry_run=False,
                confirm_live=True,
                resource_id="i-0123456789abcdef0",
                provider="aws",
            ))

        assert exc.value.status_code == 500
        assert "audit record could not be saved" in exc.value.detail
    finally:
        _current_user_id.reset(token)


def test_provider_and_region_isolation():
    from app.auth import _current_user_id
    from app.routers.recommendations import _user_state, _user_states
    token = _current_user_id.set("tenant-isolation-test")
    try:
        aws_east = _user_state("aws", "us-east")
        aws_west = _user_state("aws", "us-west")
        azure_east = _user_state("azure", "eastus")

        aws_east["dismissed"].add("rec-1")
        assert "rec-1" not in aws_west["dismissed"]
        assert "rec-1" not in azure_east["dismissed"]

        aws_east["applied"]["rec-2"] = MagicMock()
        assert "rec-2" not in aws_west["applied"]
        assert "rec-2" not in azure_east["applied"]
    finally:
        _user_states.pop("tenant-isolation-test", None)
        _current_user_id.reset(token)


def test_security_and_reliability_agents_skip_when_posture_missing():
    from app.agents import security_agent, reliability_agent
    from app.schemas import CloudMetrics

    empty_metrics = CloudMetrics(
        timestamp="2026-10-21T00:00:00Z",
        provider="aws",
        region="us-east-1",
        cpu=15.0,
        memory=30.0,
        storage=20.0,
        network=5.0,
        cost_usd_per_hour=0.05,
        carbon_gco2_per_hour=10.0,
        source="DEMO",
    )

    sec_res = security_agent.analyze(empty_metrics)
    assert sec_res["status"] == "skipped"
    assert "unavailable" in sec_res["findings"][0].lower()

    rel_res = reliability_agent.analyze(empty_metrics)
    assert rel_res["status"] == "skipped"
    assert "unavailable" in rel_res["findings"][0].lower()


def test_live_cost_returns_unavailable_when_billing_unconfigured():
    from app.cloud.aws_provider import AWSCloudProvider
    provider = AWSCloudProvider(credentials={"aws_access_key_id": "test", "aws_secret_access_key": "test"})
    # Mock is_live to True but collector has no cost explorer
    provider._is_live = True
    provider.collector = MagicMock()
    provider.collector.collect_cost_explorer.return_value = None

    cost = provider.get_cost("us-east-1")
    assert cost["source"] == "UNAVAILABLE"
    assert cost["total_usd"] is None
    assert "unavailable" in cost["note"].lower()


@pytest.mark.asyncio
async def test_audit_persistence_preserves_provider_and_region(monkeypatch):
    from app.auth import _current_user_id
    from app.database import query_audit_log
    from app.integrations.cloud_actions import CloudActionDispatcher
    from app.schemas import RecommendationItem

    token = _current_user_id.set("audit-region-user")
    try:
        rec = RecommendationItem(
            id="audit-region-rec-1",
            title="Stop idle in Ireland",
            category="cost",
            priority="high",
            description="Testing audit log region isolation",
            impact_summary="Test impact",
            estimated_monthly_savings_usd=50.0,
            estimated_carbon_reduction_pct=10.0,
            effort="low",
            action="stop_idle",
            resource_id="i-0123456789abcdef0",
        )
        res = await CloudActionDispatcher.execute_recommendation(
            rec=rec,
            dry_run=True,
            provider="aws",
            region="eu-west-1",
        )
        assert res.status == "simulated"

        # Query Ireland audit log (include_simulated=True since dry_run=True records simulated actions)
        eu_logs = await query_audit_log(provider="aws", region="eu-west-1", include_simulated=True)
        assert any(e["recommendation_id"] == "audit-region-rec-1" for e in eu_logs)

        # Query US East audit log - must NOT contain Ireland log
        us_logs = await query_audit_log(provider="aws", region="us-east-1", include_simulated=True)
        assert not any(e["recommendation_id"] == "audit-region-rec-1" for e in us_logs)
    finally:
        _current_user_id.reset(token)


@pytest.mark.asyncio
async def test_stop_idle_waiter_timeout_raises_502_and_persists_failed_audit(monkeypatch):
    from app.auth import _current_user_id
    from app.config import get_settings
    from app.database import query_audit_log
    from app.integrations.cloud_actions import CloudActionDispatcher
    from app.schemas import RecommendationItem
    from botocore.exceptions import WaiterError

    monkeypatch.setattr(get_settings(), "demo_mode", False)
    token = _current_user_id.set("waiter-timeout-user")

    class MockEC2Client:
        def describe_instances(self, **kwargs):
            return {"Reservations": [{"Instances": [{
                "InstanceId": "i-0987654321fedcba0",
                "State": {"Name": "running"},
                "InstanceLifecycle": "normal",
                "RootDeviceType": "ebs",
                "BlockDeviceMappings": [{"Ebs": {}}],
            }]}]}

        def stop_instances(self, **kwargs):
            return {}

        def get_waiter(self, name):
            class TimeoutWaiter:
                def wait(self, **kwargs):
                    raise WaiterError(name, "Max attempts exceeded", {"State": "stopping"})
            return TimeoutWaiter()

    class MockSession:
        def client(self, service_name, **kwargs):
            return MockEC2Client()

    monkeypatch.setattr("boto3.Session", lambda **kwargs: MockSession())
    monkeypatch.setattr(
        "app.integrations.cloud_actions.get_user_credentials",
        lambda provider: {
            "aws_access_key_id": "test-key",
            "aws_secret_access_key": "test-secret",
        },
    )

    try:
        rec = RecommendationItem(
            id="waiter-timeout-rec-1",
            title="Stop idle instance with timeout",
            category="cost",
            priority="high",
            description="Testing waiter timeout handling",
            impact_summary="Test impact",
            estimated_monthly_savings_usd=40.0,
            estimated_carbon_reduction_pct=5.0,
            effort="low",
            action="stop_idle",
        )
        with pytest.raises(HTTPException) as exc_info:
            await CloudActionDispatcher.execute_recommendation(
                rec=rec,
                confirm_live=True,
                resource_id="i-0987654321fedcba0",
                provider="aws",
                region="us-east-1",
            )
        assert exc_info.value.status_code == 502
        assert "Timed out waiting for instance" in exc_info.value.detail

        # Check failed audit log entry
        logs = await query_audit_log(provider="aws", region="us-east-1", statuses=["failed"])
        failed_entries = [e for e in logs if e["recommendation_id"] == "waiter-timeout-rec-1"]
        assert len(failed_entries) > 0
        assert failed_entries[0]["status"] == "failed"
    finally:
        _current_user_id.reset(token)


@pytest.mark.asyncio
async def test_rollback_waiter_timeout_raises_502_and_persists_failed_audit(monkeypatch):
    from app.auth import _current_user_id
    from app.config import get_settings
    from app.database import query_audit_log
    from app.integrations.cloud_actions import CloudActionDispatcher
    from app.schemas import RecommendationItem
    from botocore.exceptions import WaiterError

    monkeypatch.setattr(get_settings(), "demo_mode", False)
    token = _current_user_id.set("rollback-timeout-user")

    class MockEC2Client:
        def describe_instances(self, **kwargs):
            return {"Reservations": [{"Instances": [{
                "InstanceId": "i-0987654321fedcba0",
                "State": {"Name": "stopped"},
            }]}]}

        def start_instances(self, **kwargs):
            return {}

        def get_waiter(self, name):
            class TimeoutWaiter:
                def wait(self, **kwargs):
                    raise WaiterError(name, "Max attempts exceeded", {"State": "pending"})
            return TimeoutWaiter()

    class MockSession:
        def client(self, service_name, **kwargs):
            return MockEC2Client()

    monkeypatch.setattr("boto3.Session", lambda **kwargs: MockSession())
    monkeypatch.setattr(
        "app.integrations.cloud_actions.get_user_credentials",
        lambda provider: {
            "aws_access_key_id": "test-key",
            "aws_secret_access_key": "test-secret",
        },
    )

    try:
        rec = RecommendationItem(
            id="rollback-timeout-rec-1",
            title="Rollback instance with timeout",
            category="cost",
            priority="high",
            description="Testing rollback waiter timeout handling",
            impact_summary="Test impact",
            estimated_monthly_savings_usd=0.0,
            estimated_carbon_reduction_pct=0.0,
            effort="low",
            action="stop_idle",
        )
        with pytest.raises(HTTPException) as exc_info:
            await CloudActionDispatcher.rollback_recommendation(
                rec=rec,
                provider="aws",
                region="us-east-1",
                previous_state="running",
                resource_id="i-0987654321fedcba0",
            )
        assert exc_info.value.status_code == 502
        assert "Timed out waiting for instance" in exc_info.value.detail

        # Check failed audit log entry
        logs = await query_audit_log(provider="aws", region="us-east-1", statuses=["failed"])
        failed_entries = [e for e in logs if e["recommendation_id"] == "rollback-timeout-rec-1"]
        assert len(failed_entries) > 0
        assert failed_entries[0]["status"] == "failed"
    finally:
        _current_user_id.reset(token)


@pytest.mark.asyncio
async def test_batch_apply_scopes_to_provider_and_region():
    from app.auth import _current_user_id
    from app.routers.recommendations import batch_apply_recommendations, _user_state
    from app.schemas import BatchApplyRequest

    token = _current_user_id.set("batch-test-user-456")
    try:
        # Batch apply with body provider and region
        req = BatchApplyRequest(
            dry_run=True,
            provider="gcp",
            region="europe-west1",
        )
        res = await batch_apply_recommendations(req=req, provider="aws", region="us-east")
        assert res.applied_count > 0
        for r in res.results:
            assert r.dry_run is True

        # Verify GCP state was modified, AWS was untouched
        gcp_state = _user_state("gcp", "europe-west1")
        assert len(gcp_state["recommendations"]) > 0

        aws_state = _user_state("aws", "us-east")
        # In AWS state, recommendations have not been batch applied
        for r in aws_state["recommendations"]:
            assert r.status != "applied"
    finally:
        _current_user_id.reset(token)

