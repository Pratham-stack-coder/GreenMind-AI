"""Recommendations router — AI-generated optimization recommendations."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ..auth import get_current_user_id

from .. import carbon
from ..agents import orchestrator
from ..cloud import get_provider
from ..decision_engine import right_size, scaling_advice
from ..ml import predictor
from ..schemas import (
    ApplyRequest,
    ApplyResponse,
    BatchApplyRequest,
    BatchApplyResponse,
    CloudMetrics,
    ExplainResponse,
    RecommendationItem,
    RecommendationsResponse,
)

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

# Keep each user's recommendation state separate for each cloud scope.
_user_states: dict[str, dict[tuple[str, str], dict[str, Any]]] = {}


def _user_state(provider: str = "aws", region: str = "us-east") -> dict[str, Any]:
    user_id = get_current_user_id()
    if not user_id:
        raise HTTPException(status_code=401, detail="An authenticated user is required.")

    scope = (provider.lower().strip(), region.lower().strip())
    user_scopes = _user_states.setdefault(user_id, {})
    return user_scopes.setdefault(scope, {
        "recommendations": [],
        "score": 80,
        "generated": "",
        "applied": {},
        "dismissed": set(),
        "metrics": None,
    })


def _build_recommendations(provider: str, region: str) -> tuple[list[RecommendationItem], int]:
    """Fetch real or DEMO metrics from the provider factory and run agent analysis.

    DATA TRUTH:
    - In LIVE mode: uses real cloud metrics from provider API (source=LIVE_AWS/AZURE/GCP)
    - In DEMO mode or if provider is unconfigured: uses DEMO synthetic metrics (source=DEMO)
    - Agent analysis is always clearly labeled based on metrics source
    """
    state = _user_state(provider, region)
    p = get_provider(provider)
    if p.is_live:
        raw = p.get_metrics(region)
        from ..schemas import CloudMetrics
        metrics = CloudMetrics(**raw)
    else:
        from ..routers.telemetry import _generate_live_metrics
        metrics = _generate_live_metrics(provider, region)

    result = orchestrator.run(metrics)
    state = _user_state(provider, region)
    state["metrics"] = metrics
    state["recommendations"] = result.unified_recommendations
    state["score"] = result.overall_score
    state["generated"] = datetime.now(timezone.utc).isoformat()

    # Re-apply tracked state
    for rec in state["recommendations"]:
        if rec.id in state["applied"]:
            rec.status = "applied"
            rec.applied_at = state["applied"][rec.id].applied_at
            rec.steps_taken = state["applied"][rec.id].steps_taken
        elif rec.id in state["dismissed"]:
            rec.status = "dismissed"

    return state["recommendations"], state["score"]


async def _execute_apply(
    rec: RecommendationItem,
    state: dict[str, Any],
    dry_run: bool = False,
    operator_notes: str | None = None,
) -> ApplyResponse:
    from ..integrations.cloud_actions import CloudActionDispatcher

    boost = 4 if rec.priority in ("critical", "high") else 2
    target_score = state["score"] if dry_run else min(98, state["score"] + boost)

    resp = await CloudActionDispatcher.execute_recommendation(
        rec=rec,
        dry_run=dry_run,
        operator_notes=operator_notes,
        new_score=target_score,
    )

    if not dry_run:
        rec.status = "applied"
        rec.applied_at = resp.applied_at
        rec.steps_taken = resp.steps_taken
        if rec.id in state["dismissed"]:
            state["dismissed"].remove(rec.id)
        state["score"] = target_score
        state["applied"][rec.id] = resp

    return resp



@router.get("", response_model=RecommendationsResponse)
def list_recommendations(
    provider: str = Query("aws"),
    region: str = Query("us-east"),
    refresh: bool = Query(False),
    category: str | None = Query(None),
    priority: str | None = Query(None),
    status: str | None = Query(None),
):
    """Get AI-generated optimization recommendations."""
    state = _user_state(provider, region)

    if refresh or not state["recommendations"]:
        _build_recommendations(provider, region)

    recs = state["recommendations"]
    if category and category != "all":
        recs = [r for r in recs if r.category == category]
    if priority and priority != "all":
        recs = [r for r in recs if r.priority == priority]
    if status and status != "all":
        recs = [r for r in recs if r.status == status]

    return RecommendationsResponse(
        recommendations=recs,
        generated_at=state["generated"] or datetime.now(timezone.utc).isoformat(),
        optimization_score=state["score"],
    )


@router.get("/applied", response_model=list[ApplyResponse])
def list_applied_recommendations(
    provider: str = Query("aws"),
    region: str = Query("us-east"),
):
    """Get audit trail history for the selected cloud scope."""
    return list(_user_state(provider, region)["applied"].values())


@router.post("/apply-batch", response_model=BatchApplyResponse)
async def batch_apply_recommendations(
    req: BatchApplyRequest,
    provider: str = Query("aws"),
    region: str = Query("us-east"),
):
    """Batch preview recommendations in the selected cloud scope."""
    state = _user_state(provider, region)

    if not state["recommendations"]:
        _build_recommendations(provider, region)

    targets = [r for r in state["recommendations"] if r.status != "applied"]

    if req.category and req.category != "all":
        targets = [r for r in targets if r.category == req.category]
    if req.priority and req.priority != "all":
        targets = [r for r in targets if r.priority == req.priority]
    if req.recommendation_ids:
        target_ids = set(req.recommendation_ids)
        targets = [r for r in targets if r.id in target_ids]

    results: list[ApplyResponse] = []
    total_savings = 0.0
    total_carbon = 0.0

    for rec in targets:
        res = await _execute_apply(rec, state, dry_run=req.dry_run)
        results.append(res)
        total_savings += res.estimated_monthly_savings_usd
        total_carbon += res.estimated_carbon_reduction_pct

    return BatchApplyResponse(
        applied_count=sum(result.status == "applied" for result in results),
        total_monthly_savings_usd=round(total_savings, 2),
        total_carbon_reduction_pct=round(total_carbon, 2),
        results=results,
        new_score=state["score"],
    )


@router.post("/{rec_id}/apply", response_model=ApplyResponse)
async def apply_recommendation(
    rec_id: str,
    req: ApplyRequest | None = None,
    provider: str = Query("aws"),
    region: str = Query("us-east"),
):
    """Execute remediation action for a specific recommendation."""
    state = _user_state(provider, region)

    if not state["recommendations"]:
        _build_recommendations(provider, region)

    rec = next((r for r in state["recommendations"] if r.id == rec_id), None)
    if not rec:
        raise HTTPException(
            status_code=404,
            detail=f"Recommendation '{rec_id}' not found.",
        )

    dry_run = req.dry_run if req else False
    operator_notes = req.operator_notes if req else None
    return await _execute_apply(rec, state, dry_run=dry_run, operator_notes=operator_notes)


@router.post("/{rec_id}/rollback", response_model=ApplyResponse)
def rollback_recommendation(rec_id: str):
    """Return a clear error until real rollback operations are implemented."""
    raise HTTPException(
        status_code=501,
        detail="Cloud remediation rollback is not implemented.",
    )


@router.post("/{rec_id}/dismiss")
def dismiss_recommendation(
    rec_id: str,
    provider: str = Query("aws"),
    region: str = Query("us-east"),
):
    """Dismiss a recommendation in the selected cloud scope."""
    state = _user_state(provider, region)

    rec = next((r for r in state["recommendations"] if r.id == rec_id), None)
    if not rec:
        raise HTTPException(
            status_code=404,
            detail=f"Recommendation '{rec_id}' not found.",
        )

    rec.status = "dismissed"
    state["dismissed"].add(rec_id)
    state["applied"].pop(rec_id, None)
    return {"status": "dismissed", "recommendation_id": rec_id}


@router.get("/{rec_id}/explain", response_model=ExplainResponse)
def explain_recommendation(
    rec_id: str,
    provider: str = Query("aws"),
    region: str = Query("us-east"),
):
    """Explain a recommendation using the metrics and evidence from its scope."""
    state = _user_state(provider, region)
    rec = next((r for r in state["recommendations"] if r.id == rec_id), None)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation '{rec_id}' not found. Run /recommendations first.")

    feature_keys = {
        "cost": "cost",
        "performance": "cpu",
        "sustainability": "carbon",
        "security": "cpu",
        "reliability": "memory",
    }
    feature_importances = predictor.get_feature_importances()
    target_feat_imp = feature_importances.get(feature_keys.get(rec.category, "cost"), {})

    savings_str = (
        f"Estimated monthly savings: ${rec.estimated_monthly_savings_usd:.0f}."
        if rec.estimated_monthly_savings_usd > 0 else ""
    )
    carbon_str = (
        f"Estimated carbon reduction: {rec.estimated_carbon_reduction_pct:.0f}%."
        if rec.estimated_carbon_reduction_pct > 0 else ""
    )
    expected_impact = f"Projected impact: {rec.impact_summary} {savings_str} {carbon_str}".strip()
    why_flagged = "; ".join(rec.evidence) if rec.evidence else (
        f"The {rec.category} analysis generated this recommendation, but did not provide detail-level evidence."
    )

    # Only show measurements collected for this scope. Derived carbon values stay labeled estimated.
    metric_fields = {
        "cost": [
            ("cpu", "CPU utilization", "%"),
            ("memory", "Memory utilization", "%"),
            ("cost_usd_per_hour", "Hourly cost", " USD/hr"),
        ],
        "performance": [
            ("cpu", "CPU utilization", "%"),
            ("memory", "Memory utilization", "%"),
            ("network", "Network throughput", " Mbps"),
        ],
        "sustainability": [
            ("carbon_gco2_per_hour", "Carbon emissions", " gCO₂/hr"),
        ],
        "security": [],
        "reliability": [
            ("instance_count", "Reported instance count", ""),
        ],
    }
    data_evidence: list[dict[str, str]] = []
    metrics = state.get("metrics")
    if metrics is not None:
        source = getattr(metrics, "source", "UNAVAILABLE")
        for field, label, unit in metric_fields.get(rec.category, []):
            value = getattr(metrics, field, None)
            if value is None or isinstance(value, bool):
                continue
            if field == "instance_count" and not str(source).startswith("LIVE"):
                continue
            field_source = getattr(
                metrics,
                {"cost_usd_per_hour": "cost_source", "memory": "memory_source", "network": "network_source"}.get(field, ""),
                None,
            ) or source
            if field == "carbon_gco2_per_hour" and str(source).startswith("LIVE"):
                field_source = "ESTIMATED"
            formatted = f"{value:.2f}{unit}" if isinstance(value, (int, float)) else f"{value}{unit}"
            data_evidence.append({
                "metric": label,
                "observed": formatted,
                "source": str(field_source),
                "status": str(field_source),
            })

    counterfactual = (
        "A no-action outcome has not been modeled for this recommendation, so no future loss "
        "or outage is quantified here."
    )

    return ExplainResponse(
        recommendation_id=rec.id,
        title=rec.title,
        what_detected=rec.title,
        why_it_matters=why_flagged,
        evidence=rec.evidence,
        recommendation=rec.action,
        expected_impact=expected_impact,
        why_flagged=why_flagged,
        data_evidence=data_evidence,
        counterfactual=counterfactual,
        steps_to_implement=[
            "Review the recommendation evidence and its data source.",
            f"Apply the proposed action through your cloud provider: {rec.action}",
            "Verify the resulting configuration and service health.",
        ],
        expected_outcome=f"Projected outcome: {rec.impact_summary}",
        feature_importance=target_feat_imp,
    )


def get_recommendations_summary() -> dict[str, Any]:
    """Summary of active recommendations for Copilot and system intelligence."""
    state = _user_state()
    if not _user_state()["recommendations"]:
        _build_recommendations("aws", "us-east")
    open_recs = [r for r in _user_state()["recommendations"] if r.status == "open"]
    total_savings = sum(r.estimated_monthly_savings_usd for r in open_recs)
    return {
        "total_count": len(_user_state()["recommendations"]),
        "open_count": len(open_recs),
        "applied_count": len(state["applied"]),
        "score": state["score"],
        "total_savings_usd": round(total_savings, 2),
        "top_recommendations": open_recs[:3],
    }
