"""Provider action dispatcher with explicit, scoped live-operation guardrails."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from ..cloud import get_provider, get_user_credentials
from ..config import get_settings
from ..database import persist_audit_log
from ..schemas import ApplyResponse, RecommendationItem


class CloudActionFailure(RuntimeError):
    """A cloud call failed and the recovery outcome is known."""


class CloudActionDispatcher:
    """Run dry-run previews and narrowly supported live EC2 operations."""

    @classmethod
    async def execute_recommendation(
        cls,
        rec: RecommendationItem,
        dry_run: bool = False,
        operator_notes: str | None = None,
        new_score: int | None = None,
        provider: str = "aws",
        region: str = "us-east",
        confirm_live: bool = False,
        resource_id: str | None = None,
        target_instance_type: str | None = None,
    ) -> ApplyResponse:
        if dry_run:
            now_str = datetime.now(timezone.utc).isoformat()
            steps = [
                f"Prepared a preview for action: {rec.action}",
                "No cloud provider mutation was requested or performed.",
                "Savings and carbon impact remain estimates.",
            ]
            await persist_audit_log(
                rec_id=rec.id,
                title=rec.title,
                action=rec.action,
                status="simulated",
                monthly_savings=rec.estimated_monthly_savings_usd,
                carbon_reduction=rec.estimated_carbon_reduction_pct,
                new_score=new_score,
                steps_taken=steps,
                dry_run=True,
                operator_notes=operator_notes,
                provider=provider,
                region=region,
            )
            return ApplyResponse(
                recommendation_id=rec.id,
                title=rec.title,
                status="simulated",
                message=f"Preview prepared for '{rec.title}'. No cloud resources were changed.",
                estimated_monthly_savings_usd=rec.estimated_monthly_savings_usd,
                estimated_carbon_reduction_pct=rec.estimated_carbon_reduction_pct,
                applied_at=now_str,
                steps_taken=steps,
                dry_run=True,
                new_score=new_score,
            )

        if not confirm_live:
            raise HTTPException(status_code=400, detail="Explicit live-change confirmation is required.")
        if provider.strip().lower() != "aws":
            raise HTTPException(
                status_code=501,
                detail="Live changes are currently supported only for AWS EC2 idle-stop and right-size recommendations.",
            )
        if rec.action not in {"terminate_idle", "right_size_down"}:
            raise HTTPException(
                status_code=422,
                detail=f"'{rec.action}' is advisory and has no supported automatic cloud operation.",
            )
        if not resource_id or not re.fullmatch(r"i-[0-9a-fA-F]{8,17}", resource_id.strip()):
            raise HTTPException(status_code=422, detail="Enter a valid AWS EC2 instance ID.")
        if rec.action == "right_size_down" and not target_instance_type:
            raise HTTPException(status_code=422, detail="Choose a target EC2 instance type before resizing.")

        provider_client = get_provider("aws")
        if get_settings().demo_mode or not provider_client.is_live:
            raise HTTPException(
                status_code=409,
                detail="Live changes require DEMO_MODE=false and verified AWS credentials for this signed-in user.",
            )

        credentials = get_user_credentials("aws")
        try:
            result = await asyncio.to_thread(
                cls._apply_aws_ec2,
                credentials,
                region,
                resource_id.strip(),
                rec.action,
                target_instance_type.strip() if target_instance_type else None,
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=(
                    str(exc)
                    if isinstance(exc, CloudActionFailure)
                    else f"AWS did not confirm the requested change ({type(exc).__name__}). Verify the instance state before retrying."
                ),
            ) from exc

        now_str = datetime.now(timezone.utc).isoformat()
        steps = result["steps"]
        try:
            await persist_audit_log(
                rec_id=rec.id,
                title=rec.title,
                action=rec.action,
                status="applied",
                monthly_savings=rec.estimated_monthly_savings_usd,
                carbon_reduction=rec.estimated_carbon_reduction_pct,
                new_score=new_score,
                steps_taken=steps,
                dry_run=False,
                operator_notes=operator_notes,
                provider="aws",
                region=result["region"],
            )
        except Exception as exc:
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
            new_score=new_score,
        )

    @staticmethod
    def _apply_aws_ec2(
        credentials: dict[str, str],
        selected_region: str,
        resource_id: str,
        action: str,
        target_instance_type: str | None,
    ) -> dict[str, Any]:
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
        reservations = ec2.describe_instances(InstanceIds=[resource_id]).get("Reservations", [])
        instances = [instance for reservation in reservations for instance in reservation.get("Instances", [])]
        if len(instances) != 1:
            raise HTTPException(status_code=404, detail="The selected instance was not found in this account and region.")
        instance = instances[0]
        state = instance.get("State", {}).get("Name")
        if state != "running":
            raise HTTPException(status_code=409, detail=f"The selected instance must be running; current state is {state or 'unknown'}.")

        steps = [f"Verified EC2 instance {resource_id} in {aws_region}."]

        if instance.get("InstanceLifecycle") == "spot":
            raise HTTPException(status_code=422, detail="Spot instances are excluded from automated stop and resize operations.")
        if instance.get("RootDeviceType") == "instance-store" or any(
            mapping.get("Ebs") is None for mapping in instance.get("BlockDeviceMappings", [])
        ):
            raise HTTPException(status_code=422, detail="Instances with instance-store volumes cannot use automated stop or resize operations.")

        if action == "terminate_idle":
            ec2.stop_instances(InstanceIds=[resource_id])
            ec2.get_waiter("instance_stopped").wait(InstanceIds=[resource_id], WaiterConfig={"Delay": 5, "MaxAttempts": 24})
            steps.append(f"Stopped EC2 instance {resource_id}; it was not terminated.")
            return {
                "region": aws_region,
                "steps": steps,
                "message": f"EC2 instance {resource_id} is stopped. No instance was terminated.",
            }

        current_type = instance.get("InstanceType")
        if not current_type or not target_instance_type or current_type == target_instance_type:
            raise HTTPException(status_code=422, detail="A different target instance type is required.")
        info = ec2.describe_instance_types(InstanceTypes=[current_type, target_instance_type]).get("InstanceTypes", [])
        type_info = {item["InstanceType"]: item for item in info}
        if current_type not in type_info or target_instance_type not in type_info:
            raise HTTPException(status_code=422, detail="AWS could not validate both instance types in this region.")
        current_vcpu = type_info[current_type]["VCpuInfo"]["DefaultVCpus"]
        target_vcpu = type_info[target_instance_type]["VCpuInfo"]["DefaultVCpus"]
        current_memory = type_info[current_type]["MemoryInfo"]["SizeInMiB"]
        target_memory = type_info[target_instance_type]["MemoryInfo"]["SizeInMiB"]
        if target_vcpu > current_vcpu or target_memory > current_memory or (target_vcpu == current_vcpu and target_memory == current_memory):
            raise HTTPException(status_code=422, detail="The target type must use no more vCPU or memory than the current type.")
        target_type = type_info[target_instance_type]
        supported_architectures = target_type.get("ProcessorInfo", {}).get("SupportedArchitectures", [])
        if instance.get("Architecture") and instance["Architecture"] not in supported_architectures:
            raise HTTPException(status_code=422, detail="The target type is incompatible with this instance architecture.")
        supported_virtualization = target_type.get("SupportedVirtualizationTypes", [])
        if instance.get("VirtualizationType") and instance["VirtualizationType"] not in supported_virtualization:
            raise HTTPException(status_code=422, detail="The target type is incompatible with this instance virtualization type.")

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
        return {
            "region": aws_region,
            "steps": steps,
            "message": f"Resized EC2 instance {resource_id} from {current_type} to {target_instance_type}.",
        }

    @classmethod
    def rollback_recommendation(cls, rec: RecommendationItem, **kwargs: Any) -> ApplyResponse:
        raise HTTPException(
            status_code=501,
            detail="Rollback is not available yet. Stop operations can be manually reversed by starting the instance; resize changes require an explicit previous type.",
        )
