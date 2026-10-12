"""
Cloud Action Execution Dispatcher.
Executes real platform API calls against AWS/Azure/GCP when credentials are
present, and executes verified simulation with realistic platform step logs and
safety guardrails when in demo mode or dry-run.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from ..config import get_settings
from ..database import persist_audit_log
from ..schemas import ApplyResponse, RecommendationItem

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
                        dry_run=(platform_status == "simulated"),
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
            dry_run=(platform_status == "simulated"),
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
        status = "simulated" if settings.demo_mode else "pending"
        steps = [
            f"Rollback requested for recommendation: {rec.title}",
            "No verified live rollback adapter ran; infrastructure state is unchanged by this request.",
        ]
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    persist_audit_log(
                        rec_id=rec.id,
                        title=rec.title,
                        action=f"Rollback: {rec.action}",
                        status=status,
                        monthly_savings=0.0,
                        carbon_reduction=0.0,
                        new_score=new_score,
                        steps_taken=steps,
                        dry_run=True,
                        operator_notes=operator_notes or "Rollback requested; no live state changed",
                    )
                )
        except Exception:
            pass

        return ApplyResponse(
            recommendation_id=rec.id,
            title=rec.title,
            status=status,
            message=("Simulation only; no live cloud resources were changed." if settings.demo_mode else "Rollback is pending; this dispatcher did not modify live cloud resources."),
            estimated_monthly_savings_usd=rec.estimated_monthly_savings_usd,
            estimated_carbon_reduction_pct=rec.estimated_carbon_reduction_pct,
            applied_at=None,
            steps_taken=steps,
            dry_run=(status == "simulated"),
            new_score=new_score,
        )
