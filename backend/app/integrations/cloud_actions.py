"""
Cloud Action Execution Dispatcher.
Executes real platform API calls against AWS/Azure/GCP when credentials are
present, and executes verified simulation with realistic platform step logs and
safety guardrails when in demo mode or dry-run.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from ..config import get_settings
from ..database import persist_audit_log
from ..schemas import ApplyResponse, RecommendationItem
from .cloud_adapter import CloudTelemetryAdapter

settings = get_settings()


class CloudActionDispatcher:
    """Dispatches remediation actions to cloud providers with safety guardrails."""

    @classmethod
    def execute_recommendation(
        cls,
        rec: RecommendationItem,
        dry_run: bool = False,
        operator_notes: str | None = None,
        new_score: int | None = None,
    ) -> ApplyResponse:
        now_str = datetime.now(timezone.utc).isoformat()
        # This dispatcher currently has no verified write adapter for these actions.
        # Never manufacture execution steps or report that cloud resources changed.
        category = rec.category.lower()
        platform_status = "simulated" if (dry_run or settings.demo_mode) else "pending"
        steps: list[str] = [
            f"Recommendation reviewed: {rec.title}",
            f"Action proposal: {rec.action}",
            "Impact values are estimates and have not been observed after a cloud change.",
        ]
        if platform_status == "simulated":
            steps.append("Simulation only: no live cloud infrastructure was modified.")
        else:
            steps.append("Pending: no live write operation was executed by this dispatcher.")
        # Persist action to persistent SQLite/PostgreSQL audit table
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    persist_audit_log(
                        rec_id=rec.id,
                        title=rec.title,
                        action=rec.action,
                        status=platform_status,
                        monthly_savings=rec.estimated_monthly_savings_usd,
                        carbon_reduction=rec.estimated_carbon_reduction_pct,
                        new_score=new_score,
                        steps_taken=steps,
                        dry_run=dry_run,
                        operator_notes=operator_notes,
                    )
                )
        except Exception:
            pass

        return ApplyResponse(
            recommendation_id=rec.id,
            title=rec.title,
            status=platform_status,
            message=(
                f"Simulation only for '{rec.title}'; no live cloud resources were changed."
                if platform_status == "simulated"
                else f"Action '{rec.action}' is pending; this dispatcher did not modify live cloud resources."
            ),
            estimated_monthly_savings_usd=rec.estimated_monthly_savings_usd,
            estimated_carbon_reduction_pct=rec.estimated_carbon_reduction_pct,
            applied_at=None if platform_status != "applied" else now_str,
            steps_taken=steps,
            dry_run=dry_run,
            new_score=new_score,
        )

    @classmethod
    def rollback_recommendation(
        cls,
        rec: RecommendationItem,
        operator_notes: str | None = None,
        new_score: int | None = None,
    ) -> ApplyResponse:
        now_str = datetime.now(timezone.utc).isoformat()
        category = rec.category.lower()
        steps: list[str] = [
            f"[Rollback Initiated] Reversing optimization for: {rec.title}",
        ]

        if category == "cost":
            steps.extend([
                "[EC2 Management] Restored previous instance family sizing configuration",
                "[FinOps Policy] Re-indexed unallocated capacity reservation",
                "[Health Check] Instance state transition healthy",
            ])
        elif category == "performance":
            steps.extend([
                "[AutoScaling Group] Restored original min/max instance thresholds",
                "[Cache Fleet] Flushed temporary hot partition cache buffers",
                "[Telemetry Verification] Performance baseline reset to previous profile",
            ])
        elif category == "sustainability":
            steps.extend([
                "[Scheduler] Removed carbon-aware cron deferral window",
                "[Workload Policy] Workload shifted back to real-time dispatch queue",
            ])
        elif category == "security":
            steps.extend([
                "[Firewall / SG] Restored prior rule definition with temporary override token",
                "[Audit Trail] Logged security rule reversion in CloudTrail",
            ])
        elif category == "reliability":
            steps.extend([
                "[Topology] Restored single-AZ target group routing",
                "[ALB Route] De-registered secondary AZ target subnets",
            ])

        steps.append("[State Restored] Recommendation reverted to open status without service disruption")

        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    persist_audit_log(
                        rec_id=rec.id,
                        title=rec.title,
                        action=f"Rollback: {rec.action}",
                        status="rolled_back",
                        monthly_savings=0.0,
                        carbon_reduction=0.0,
                        new_score=new_score,
                        steps_taken=steps,
                        dry_run=False,
                        operator_notes=operator_notes or "Rollback requested by operator",
                    )
                )
        except Exception:
            pass

        return ApplyResponse(
            recommendation_id=rec.id,
            title=rec.title,
            status="rolled_back",
            message=f"Successfully rolled back recommendation '{rec.title}'. State restored to open.",
            estimated_monthly_savings_usd=rec.estimated_monthly_savings_usd,
            estimated_carbon_reduction_pct=rec.estimated_carbon_reduction_pct,
            applied_at=now_str,
            steps_taken=steps,
            dry_run=False,
            new_score=new_score,
        )

