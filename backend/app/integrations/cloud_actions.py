"""
Cloud Action Dispatcher.
Executes dry-run previews, digital twin simulations, and verified real cloud remediation actions
with safety guardrails, pre-flight validation, and post-action verification.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from ..cloud import get_provider, get_user_credentials
from ..config import get_settings
from ..database import persist_audit_log
from ..schemas import ApplyResponse, RecommendationItem

logger = logging.getLogger(__name__)
settings = get_settings()


class CloudActionFailure(Exception):
    """Raised when a cloud remediation operation fails or cannot be verified."""
    pass


class CloudActionDispatcher:
    """Dispatches remediation actions to cloud providers with safety guardrails."""

    @classmethod
    async def execute_recommendation(
        cls,
        rec: RecommendationItem,
        dry_run: bool = False,
        simulate: bool = False,
        confirm_live: bool = False,
        resource_id: str | None = None,
        target_instance_type: str | None = None,
        operator_notes: str | None = None,
        provider: str = "aws",
        region: str = "us-east",
        new_score: int | None = None,
        baseline_score: int | None = None,
        projected_score: int | None = None,
        score_delta: int | None = None,
        assumptions: list[str] | None = None,
    ) -> ApplyResponse:
        """
        Execute either an honest dry-run / simulation or a safe, verified real cloud mutation.
        """
        now_str = datetime.now(timezone.utc).isoformat()
        proj = projected_score if projected_score is not None else new_score
        delta_str = f" ({score_delta:+d} pts)" if score_delta is not None and score_delta != 0 else ""

        # ── 1. Dry-run preview or Digital Twin simulation ────────────────────────
        if dry_run or simulate:
            steps = [
                f"Previewed the proposed action: {rec.action}",
                f"Baseline score: {baseline_score if baseline_score is not None else 'N/A'}/100",
                f"Projected score: {proj if proj is not None else 'N/A'}/100{delta_str}",
                "No cloud provider mutation was requested or performed.",
                "Estimated savings and carbon impact remain projections.",
            ]
            try:
                await persist_audit_log(
                    rec_id=rec.id,
                    title=rec.title,
                    action=rec.action,
                    status="simulated",
                    monthly_savings=rec.estimated_monthly_savings_usd,
                    carbon_reduction=rec.estimated_carbon_reduction_pct,
                    new_score=proj,
                    steps_taken=steps,
                    dry_run=True,
                    operator_notes=operator_notes,
                )
            except Exception as exc:
                logger.warning(f"Failed to persist dry-run audit log: {exc}")

            return ApplyResponse(
                recommendation_id=rec.id,
                title=rec.title,
                status="simulated",
                message=f"Dry run completed for '{rec.title}'. No cloud resources were changed.",
                estimated_monthly_savings_usd=rec.estimated_monthly_savings_usd,
                estimated_carbon_reduction_pct=rec.estimated_carbon_reduction_pct,
                applied_at=now_str,
                steps_taken=steps,
                dry_run=True,
                verified=False,
                verification_status="simulated",
                new_score=proj,
                baseline_score=baseline_score,
                projected_score=proj,
                score_delta=score_delta,
                assumptions=assumptions or [],
            )

        # ── 2. Real Cloud Remediation (Live Mutation Guardrails) ─────────────────
        # Safety Check 1: Explicit Confirmation
        if not confirm_live:
            raise HTTPException(
                status_code=501,
                detail=(
                    "Live cloud remediation is not implemented for unconfirmed actions. "
                    "Use dry_run=true to preview this action or provide explicit confirmation "
                    "(confirm_live=true) for supported actions."
                ),
            )

        # Safety Check 2: Provider Support Scope
        normalized_provider = (provider or "aws").strip().lower()
        if normalized_provider != "aws":
            raise HTTPException(
                status_code=501,
                detail=(
                    f"Live cloud remediation for provider '{normalized_provider}' is not implemented. "
                    "Currently, automated mutation is only supported for AWS EC2 instances."
                ),
            )

        # Safety Check 3: Action Support Scope
        normalized_action = (rec.action or "").strip().lower()
        supported_actions = ("terminate_idle", "stop_idle", "right_size_down", "right_size")
        if normalized_action not in supported_actions:
            raise HTTPException(
                status_code=501,
                detail=(
                    f"Live cloud remediation for action '{rec.action}' is not implemented. "
                    "Supported live actions: idle instance stopping (terminate_idle) and "
                    "compute instance downsizing (right_size_down)."
                ),
            )

        # Safety Check 4: Credentials and Demo Mode
        if settings.demo_mode:
            raise HTTPException(
                status_code=422,
                detail="System is operating in DEMO_MODE. Live infrastructure mutation is disabled to protect cloud resources.",
            )

        credentials = get_user_credentials("aws")
        if not credentials.get("aws_access_key_id") or not credentials.get("aws_secret_access_key"):
            aws_prov = get_provider("aws")
            if not getattr(aws_prov, "is_configured", False):
                raise HTTPException(
                    status_code=422,
                    detail="Live cloud remediation requires authenticated AWS credentials. Configure AWS credentials in Settings before applying live changes.",
                )
            collector = getattr(aws_prov, "collector", None)
            credentials = {
                "aws_access_key_id": getattr(collector, "_default_access_key_id", ""),
                "aws_secret_access_key": getattr(collector, "_default_secret_access_key", ""),
                "aws_session_token": getattr(collector, "_default_session_token", "") or "",
                "aws_default_region": getattr(collector, "_default_region", region),
            }

        # Safety Check 5: Resource Identifier
        target_res_id = (resource_id or getattr(rec, "resource_id", None) or "").strip()
        if not target_res_id:
            raise HTTPException(
                status_code=400,
                detail="A valid AWS EC2 instance ID (resource_id) is required for live remediation.",
            )

        # ── 3. Execute Validated AWS Operation ──────────────────────────────────
        try:
            result = cls._apply_aws_ec2(
                credentials=credentials,
                selected_region=region,
                resource_id=target_res_id,
                action=normalized_action,
                target_instance_type=target_instance_type,
            )
        except HTTPException:
            raise
        except CloudActionFailure as exc:
            raise HTTPException(
                status_code=502,
                detail=f"AWS operation failed: {exc}",
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error executing AWS action: {exc}",
            ) from exc

        steps = result.get("steps", [])
        verified_score = proj

        # ── 4. Audit Trail Persistence ──────────────────────────────────────────
        try:
            await persist_audit_log(
                rec_id=rec.id,
                title=rec.title,
                action=rec.action,
                status="applied",
                monthly_savings=rec.estimated_monthly_savings_usd,
                carbon_reduction=rec.estimated_carbon_reduction_pct,
                new_score=verified_score,
                steps_taken=steps,
                dry_run=False,
                operator_notes=operator_notes,
            )
        except Exception as exc:
            logger.error(f"Failed to persist audit log: {exc}")
            raise HTTPException(
                status_code=500,
                detail="AWS confirmed the change, but its audit record could not be saved. Verify the instance in AWS before retrying.",
            ) from exc

        return ApplyResponse(
            recommendation_id=rec.id,
            title=rec.title,
            status="applied",
            message=result["message"],
            estimated_monthly_savings_usd=rec.estimated_monthly_savings_usd,
            estimated_carbon_reduction_pct=rec.estimated_carbon_reduction_pct,
            applied_at=now_str,
            steps_taken=steps,
            dry_run=False,
            verified=True,
            verification_status="verified",
            resource_id=target_res_id,
            provider="aws",
            region=result.get("region", region),
            previous_state=result.get("previous_state"),
            current_state=result.get("current_state"),
            new_score=verified_score,
            baseline_score=baseline_score,
            projected_score=proj,
            score_delta=score_delta,
            assumptions=assumptions or [],
        )

    @staticmethod
    def _apply_aws_ec2(
        credentials: dict[str, str],
        selected_region: str,
        resource_id: str,
        action: str,
        target_instance_type: str | None,
    ) -> dict[str, Any]:
        """
        Executes pre-flight verified mutation on an AWS EC2 instance.
        """
        import boto3

        region_aliases = {
            "us-east": "us-east-1",
            "us-west": "us-west-2",
            "eu-west": "eu-west-1",
            "ap-southeast": "ap-southeast-1",
            "ca-central": "ca-central-1",
            "in-north": "ap-south-1",
        }
        aws_region = region_aliases.get(selected_region.strip().lower(), selected_region.strip())

        session = boto3.Session(
            aws_access_key_id=credentials.get("aws_access_key_id"),
            aws_secret_access_key=credentials.get("aws_secret_access_key"),
            aws_session_token=credentials.get("aws_session_token") or None,
            region_name=aws_region,
        )
        ec2 = session.client("ec2")

        # Query and validate instance exists
        try:
            reservations = ec2.describe_instances(InstanceIds=[resource_id]).get("Reservations", [])
        except Exception as exc:
            raise HTTPException(
                status_code=404,
                detail=f"AWS EC2 describe_instances error for {resource_id}: {exc}",
            ) from exc

        instances = [inst for reservation in reservations for inst in reservation.get("Instances", [])]
        if len(instances) != 1:
            raise HTTPException(
                status_code=404,
                detail="The selected instance was not found in this account and region.",
            )

        instance = instances[0]
        state = instance.get("State", {}).get("Name")
        if state != "running":
            raise HTTPException(
                status_code=409,
                detail=f"The selected instance must be running; current state is {state or 'unknown'}.",
            )

        steps = [f"Verified EC2 instance {resource_id} in {aws_region} (state: {state})."]

        # Safeguards: Exclude spot and instance-store instances
        if instance.get("InstanceLifecycle") == "spot":
            raise HTTPException(
                status_code=422,
                detail="Spot instances are excluded from automated stop and resize operations.",
            )
        if instance.get("RootDeviceType") == "instance-store" or any(
            mapping.get("Ebs") is None for mapping in instance.get("BlockDeviceMappings", [])
        ):
            raise HTTPException(
                status_code=422,
                detail="Instances with instance-store volumes cannot use automated stop or resize operations.",
            )

        # ── Action A: Stop Idle Instance (Safe, Non-Destructive Stopping) ────────
        if action in ("terminate_idle", "stop_idle"):
            ec2.stop_instances(InstanceIds=[resource_id])
            waiter = ec2.get_waiter("instance_stopped")
            waiter.wait(InstanceIds=[resource_id], WaiterConfig={"Delay": 5, "MaxAttempts": 24})
            steps.append(f"Stopped EC2 instance {resource_id}; EBS data preserved (not terminated).")

            # Post-action verification
            verify_reservations = ec2.describe_instances(InstanceIds=[resource_id]).get("Reservations", [])
            post_instances = [inst for res in verify_reservations for inst in res.get("Instances", [])]
            post_state = post_instances[0].get("State", {}).get("Name") if post_instances else "unknown"
            if post_state != "stopped":
                raise CloudActionFailure(
                    f"Verification failed: expected instance {resource_id} to be 'stopped', but found '{post_state}'."
                )
            steps.append(f"Verified instance {resource_id} state is 'stopped'.")

            return {
                "region": aws_region,
                "steps": steps,
                "previous_state": "running",
                "current_state": "stopped",
                "message": f"EC2 instance {resource_id} is safely stopped and verified. No instance was terminated.",
            }

        # ── Action B: Downsize / Right-Size Compute Instance ────────────────────
        current_type = instance.get("InstanceType")
        if not current_type or not target_instance_type or current_type == target_instance_type:
            raise HTTPException(
                status_code=422,
                detail="A different target instance type is required for downsizing.",
            )

        info = ec2.describe_instance_types(InstanceTypes=[current_type, target_instance_type]).get("InstanceTypes", [])
        type_info = {item["InstanceType"]: item for item in info}
        if current_type not in type_info or target_instance_type not in type_info:
            raise HTTPException(
                status_code=422,
                detail="AWS could not validate both instance types in this region.",
            )

        current_vcpu = type_info[current_type]["VCpuInfo"]["DefaultVCpus"]
        target_vcpu = type_info[target_instance_type]["VCpuInfo"]["DefaultVCpus"]
        current_memory = type_info[current_type]["MemoryInfo"]["SizeInMiB"]
        target_memory = type_info[target_instance_type]["MemoryInfo"]["SizeInMiB"]

        if target_vcpu > current_vcpu or target_memory > current_memory or (target_vcpu == current_vcpu and target_memory == current_memory):
            raise HTTPException(
                status_code=422,
                detail="The target type must use no more vCPU or memory than the current type.",
            )

        target_type = type_info[target_instance_type]
        supported_architectures = target_type.get("ProcessorInfo", {}).get("SupportedArchitectures", [])
        if instance.get("Architecture") and instance["Architecture"] not in supported_architectures:
            raise HTTPException(
                status_code=422,
                detail="The target type is incompatible with this instance architecture.",
            )

        supported_virtualization = target_type.get("SupportedVirtualizationTypes", [])
        if instance.get("VirtualizationType") and instance["VirtualizationType"] not in supported_virtualization:
            raise HTTPException(
                status_code=422,
                detail="The target type is incompatible with this instance virtualization type.",
            )

        # Stop -> Modify -> Restart with Waiters & Automated Recovery
        ec2.stop_instances(InstanceIds=[resource_id])
        ec2.get_waiter("instance_stopped").wait(InstanceIds=[resource_id], WaiterConfig={"Delay": 5, "MaxAttempts": 24})
        steps.append(f"Stopped {resource_id} before changing its instance type.")

        try:
            ec2.modify_instance_attribute(InstanceId=resource_id, InstanceType={"Value": target_instance_type})
            steps.append(f"Changed instance type from {current_type} to {target_instance_type}.")
            ec2.start_instances(InstanceIds=[resource_id])
            ec2.get_waiter("instance_running").wait(InstanceIds=[resource_id], WaiterConfig={"Delay": 5, "MaxAttempts": 24})
            steps.append(f"Started {resource_id} and confirmed the running state.")
        except Exception as exc:
            try:
                ec2.modify_instance_attribute(InstanceId=resource_id, InstanceType={"Value": current_type})
                ec2.start_instances(InstanceIds=[resource_id])
                ec2.get_waiter("instance_running").wait(InstanceIds=[resource_id], WaiterConfig={"Delay": 5, "MaxAttempts": 24})
            except Exception as recovery_exc:
                raise CloudActionFailure(
                    f"Resize failed and automatic recovery was not confirmed. {resource_id} may be stopped; inspect it in AWS before retrying."
                ) from recovery_exc
            raise CloudActionFailure(
                f"Resize failed, but {resource_id} was restored to {current_type} and confirmed running."
            ) from exc

        # Post-action verification
        verify_reservations = ec2.describe_instances(InstanceIds=[resource_id]).get("Reservations", [])
        post_instances = [inst for res in verify_reservations for inst in res.get("Instances", [])]
        post_type = post_instances[0].get("InstanceType") if post_instances else None
        post_state = post_instances[0].get("State", {}).get("Name") if post_instances else None

        if post_type != target_instance_type or post_state != "running":
            raise CloudActionFailure(
                f"Verification failed: instance {resource_id} is '{post_type}' in state '{post_state}', "
                f"expected '{target_instance_type}' in 'running'."
            )
        steps.append(f"Verified instance {resource_id} is running with new type {target_instance_type}.")

        return {
            "region": aws_region,
            "steps": steps,
            "previous_state": current_type,
            "current_state": target_instance_type,
            "message": f"Resized EC2 instance {resource_id} from {current_type} to {target_instance_type} and verified running state.",
        }

    @classmethod
    async def rollback_recommendation(
        cls,
        rec: RecommendationItem,
        operator_notes: str | None = None,
        provider: str = "aws",
        region: str = "us-east",
        previous_state: str | None = None,
        resource_id: str | None = None,
    ) -> ApplyResponse:
        """
        Execute safe rollback for reversible actions where prior state is recorded.
        """
        now_str = datetime.now(timezone.utc).isoformat()
        normalized_action = (rec.action or "").strip().lower()

        if not resource_id:
            raise HTTPException(
                status_code=400,
                detail="Resource identifier is required to execute rollback.",
            )

        credentials = get_user_credentials("aws")
        if not credentials.get("aws_access_key_id"):
            aws_prov = get_provider("aws")
            collector = getattr(aws_prov, "collector", None)
            credentials = {
                "aws_access_key_id": getattr(collector, "_default_access_key_id", ""),
                "aws_secret_access_key": getattr(collector, "_default_secret_access_key", ""),
                "aws_session_token": getattr(collector, "_default_session_token", "") or "",
                "aws_default_region": getattr(collector, "_default_region", region),
            }

        # ── Reversible Stop: Rollback by restarting instance ─────────────────────
        if normalized_action in ("terminate_idle", "stop_idle"):
            import boto3
            region_aliases = {
                "us-east": "us-east-1", "us-west": "us-west-2", "eu-west": "eu-west-1",
                "ap-southeast": "ap-southeast-1", "ca-central": "ca-central-1", "in-north": "ap-south-1",
            }
            aws_region = region_aliases.get(region.strip().lower(), region.strip())
            session = boto3.Session(
                aws_access_key_id=credentials.get("aws_access_key_id"),
                aws_secret_access_key=credentials.get("aws_secret_access_key"),
                aws_session_token=credentials.get("aws_session_token") or None,
                region_name=aws_region,
            )
            ec2 = session.client("ec2")
            ec2.start_instances(InstanceIds=[resource_id])
            ec2.get_waiter("instance_running").wait(InstanceIds=[resource_id], WaiterConfig={"Delay": 5, "MaxAttempts": 24})
            steps = [
                f"Initiated rollback for recommendation {rec.id}.",
                f"Restarted EC2 instance {resource_id} in {aws_region}.",
                "Verified instance running state after rollback.",
            ]

            await persist_audit_log(
                rec_id=rec.id,
                title=rec.title,
                action=rec.action,
                status="rolled_back",
                monthly_savings=0.0,
                carbon_reduction=0.0,
                new_score=None,
                steps_taken=steps,
                dry_run=False,
                operator_notes=operator_notes,
            )

            return ApplyResponse(
                recommendation_id=rec.id,
                title=rec.title,
                status="rolled_back",
                message=f"Rollback successful: EC2 instance {resource_id} was restarted and verified running.",
                estimated_monthly_savings_usd=0.0,
                estimated_carbon_reduction_pct=0.0,
                applied_at=now_str,
                steps_taken=steps,
                dry_run=False,
                verified=True,
                verification_status="verified",
                resource_id=resource_id,
                provider="aws",
                region=aws_region,
                previous_state="stopped",
                current_state="running",
            )

        # ── Reversible Resize: Rollback to previous instance type ────────────────
        if normalized_action in ("right_size_down", "right_size") and previous_state:
            res = cls._apply_aws_ec2(
                credentials=credentials,
                selected_region=region,
                resource_id=resource_id,
                action="right_size",
                target_instance_type=previous_state,
            )
            steps = [f"Rollback: reverted {resource_id} to previous type {previous_state}."] + res.get("steps", [])
            await persist_audit_log(
                rec_id=rec.id,
                title=rec.title,
                action=rec.action,
                status="rolled_back",
                monthly_savings=0.0,
                carbon_reduction=0.0,
                new_score=None,
                steps_taken=steps,
                dry_run=False,
                operator_notes=operator_notes,
            )
            return ApplyResponse(
                recommendation_id=rec.id,
                title=rec.title,
                status="rolled_back",
                message=f"Rollback successful: EC2 instance {resource_id} was restored to {previous_state}.",
                estimated_monthly_savings_usd=0.0,
                estimated_carbon_reduction_pct=0.0,
                applied_at=now_str,
                steps_taken=steps,
                dry_run=False,
                verified=True,
                verification_status="verified",
                resource_id=resource_id,
                provider="aws",
                region=res.get("region", region),
                previous_state=res.get("previous_state"),
                current_state=res.get("current_state"),
            )

        raise HTTPException(
            status_code=501,
            detail="Cloud remediation rollback is not implemented for this action without a recorded prior state.",
        )
