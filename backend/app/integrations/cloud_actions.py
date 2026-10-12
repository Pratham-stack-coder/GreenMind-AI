"""
Cloud Action Dispatcher.
Returns dry-run previews and rejects live remediation until provider mutations
and rollback state tracking are implemented.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException

from ..database import persist_audit_log
from ..schemas import ApplyResponse, RecommendationItem


class CloudActionDispatcher:
    """Dispatches remediation actions to cloud providers with safety guardrails."""

    @classmethod
    async def execute_recommendation(
        cls,
        rec: RecommendationItem,
        dry_run: bool = False,
        operator_notes: str | None = None,
        new_score: int | None = None,
    ) -> ApplyResponse:
        """Return an honest dry-run result; live mutation is not implemented."""
        if not dry_run:
            raise HTTPException(
                status_code=501,
                detail="Live cloud remediation is not implemented. Use dry_run=true to preview this action.",
            )

        now_str = datetime.now(timezone.utc).isoformat()
        steps = [
            f"Previewed the proposed action: {rec.action}",
            "No cloud provider mutation was requested or performed.",
            "Estimated savings and carbon impact remain projections.",
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
        )

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
            new_score=new_score,
        )

    @classmethod
    def rollback_recommendation(
        cls,
        rec: RecommendationItem,
        operator_notes: str | None = None,
        new_score: int | None = None,
    ) -> ApplyResponse:
        """Reject rollback until real provider mutation and state tracking exist."""
        raise HTTPException(
            status_code=501,
            detail="Cloud remediation rollback is not implemented.",
        )
