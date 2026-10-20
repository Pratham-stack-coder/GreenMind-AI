"""Recommendations router — AI-generated optimization recommendations and lifecycle management."""

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
from ..services.scoring import compute_optimization_scores

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

# Keep each user's recommendation state separate for each cloud scope.
_user_states: dict[str, dict[tuple[str, str], dict[str, Any]]] = {}


def _user_state(provider: str = "aws", region: str = "us-east") -> dict[str, Any]:
    user_id = get_current_user_id()
    if not user_id:
        raise HTTPException(status_code=401, detail="An authenticated user is required.")

    scope = (str(provider or "aws").strip().lower(), str(region or "us-east").strip().lower())
    user_scopes = _user_states.setdefault(user_id, {})
    return user_scopes.setdefault(scope, {
        "recommendations": [],
        "score": 80,
        "baseline_score": 80,
        "generated": "",
        "applied": {},
        "simulated": {},
        "dismissed": set(),
        "baseline_metrics": None,
        "simulated_metrics": None,
        "metrics": None,
    })


def get_user_simulation_state(user_id: str | None = None, provider: str = "aws", region: str = "us-east") -> dict[str, Any] | None:
    """Read simulated state for the authenticated user, accessible by analytics router."""
    if not user_id:
        user_id = get_current_user_id()
    if not user_id or user_id not in _user_states:
        return None
    scope = (str(provider or "aws").strip().lower(), str(region or "us-east").strip().lower())
    user_scopes = _user_states[user_id]
    st = user_scopes.get(scope)
    if not st or not st.get("simulated"):
        return None
    return {
        "simulated_recommendations": st["simulated"],
        "simulated_metrics": st.get("simulated_metrics"),
        "baseline_metrics": st.get("baseline_metrics"),
        "baseline_score": st.get("baseline_score", st.get("score")),
        "score": st.get("score"),
    }


def _simulate_metrics_for_recommendations(
    baseline: CloudMetrics,
    recs: list[RecommendationItem],
) -> CloudMetrics:
    """
    Project after-state infrastructure metrics resulting from a set of recommendations.
    Uses Digital Twin scenario principles:
    - Right-sizing moves underutilized CPU into optimal utilization band (35-70%) and cuts cost/carbon.
    - Scale up relieves CPU saturation but increases cost.
    - Terminating idle nodes reduces cost and removes dead utilization penalties.
    - Time-shifting or regional shifts cut Scope 2 carbon intensity.
    - Non-telemetry recommendations leave telemetry metrics untouched.
    """
    data = baseline.model_dump()
    cpu = data.get("cpu", 50.0)
    memory = data.get("memory")
    cost = data.get("cost_usd_per_hour", 0.192)
    carbon_val = data.get("carbon_gco2_per_hour", 35.0)
    count = data.get("instance_count", 1)

    for rec in recs:
        action = (rec.action or "").lower().strip()
        category = (rec.category or "").lower().strip()

        if action in ("stop_idle", "terminate_idle", "terminate") or "terminate" in action or "stop_idle" in action:
            # Stop idle node (capacity removed from active pool)
            count = max(1, count - 1)
            cost = max(0.01, round(cost - (rec.estimated_monthly_savings_usd / 720.0), 4))
            if cpu < 20.0:
                cpu = 45.0  # Removing idle instance elevates remaining cluster utilization
        elif action in ("right_size", "right_size_green") or "right_size" in action:
            # Right size to optimal family
            if cpu < 25.0:
                cpu = round(min(70.0, max(38.0, cpu * 1.8)), 1)
            elif cpu > 75.0:
                cpu = round(cpu * 0.88, 1)
            cost = max(0.01, round(cost - (rec.estimated_monthly_savings_usd / 720.0), 4))
            if rec.estimated_carbon_reduction_pct > 0:
                carbon_val = round(max(0.01, carbon_val * (1.0 - rec.estimated_carbon_reduction_pct / 100.0)), 2)
        elif action in ("scale_out", "scale_up") or "scale_up" in action:
            # Scale out adds capacity
            count += 1
            cpu = round(max(15.0, cpu * 0.55), 1)
            if memory is not None:
                memory = round(max(20.0, memory * 0.60), 1)
            cost = round(cost * 1.55, 4)
        elif action in ("scale_in", "scale_down") or "scale_down" in action:
            # Scale in removes capacity
            if count > 1:
                count -= 1
                cpu = round(min(95.0, cpu * 1.6), 1)
                cost = max(0.01, round(cost * 0.60, 4))
        elif action in ("time_shift_batch", "region_migration", "region_migrate") or category == "sustainability":
            # Carbon abatement
            if rec.estimated_carbon_reduction_pct > 0:
                carbon_val = round(max(0.01, carbon_val * (1.0 - rec.estimated_carbon_reduction_pct / 100.0)), 2)

    data["cpu"] = cpu
    data["memory"] = memory
    data["cost_usd_per_hour"] = cost
    data["carbon_gco2_per_hour"] = carbon_val
    data["instance_count"] = count
    data["source"] = "SIMULATED"
    return CloudMetrics(**data)


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
        metrics = CloudMetrics(**raw)
    else:
        from ..routers.telemetry import _generate_live_metrics
        metrics = _generate_live_metrics(provider, region)

    result = orchestrator.run(metrics)
    state = _user_state(provider, region)
    state["recommendations"] = result.unified_recommendations
    state["baseline_metrics"] = metrics
    state["metrics"] = metrics

    # Baseline scores calculated with shared scoring function
    base_scores = compute_optimization_scores(metrics, region=region, source=metrics.source)
    state["baseline_score"] = base_scores.overall

    # Re-apply tracked state (applied, simulated, dismissed)
    for rec in state["recommendations"]:
        if rec.id in state["applied"]:
            rec.status = "applied"
            rec.applied_at = state["applied"][rec.id].applied_at
            rec.steps_taken = state["applied"][rec.id].steps_taken
        elif rec.id in state["simulated"]:
            rec.status = "simulated"
            rec.applied_at = state["simulated"][rec.id].applied_at
            rec.steps_taken = state["simulated"][rec.id].steps_taken
        elif rec.id in state["dismissed"]:
            rec.status = "dismissed"

    # If there are active simulated optimizations, recalculate projected score
    sim_recs = [r for r in state["recommendations"] if r.status == "simulated"]
    if sim_recs:
        after_metrics = _simulate_metrics_for_recommendations(metrics, sim_recs)
        state["simulated_metrics"] = after_metrics
        proj_scores = compute_optimization_scores(
            after_metrics,
            region=region,
            source="SIMULATED",
            is_simulated=True,
            baseline_overall=base_scores.overall,
        )
        state["score"] = proj_scores.overall
    else:
        state["simulated_metrics"] = None
        state["score"] = base_scores.overall

    state["generated"] = datetime.now(timezone.utc).isoformat()
    return state["recommendations"], state["score"]


async def _execute_apply(
    rec: RecommendationItem,
    dry_run: bool = False,
    simulate: bool = False,
    confirm_live: bool = False,
    resource_id: str | None = None,
    target_instance_type: str | None = None,
    operator_notes: str | None = None,
    provider: str = "aws",
    region: str = "us-east",
) -> ApplyResponse:
    state = _user_state(provider, region)
    from ..integrations.cloud_actions import CloudActionDispatcher
    from ..database import persist_recommendation_state

    base_metrics = state.get("baseline_metrics")
    if base_metrics is None:
        from ..routers.telemetry import _generate_live_metrics
        base_metrics = _generate_live_metrics(provider, region)
        state["baseline_metrics"] = base_metrics

    # Calculate baseline scores
    base_scores = compute_optimization_scores(
        base_metrics,
        region=base_metrics.region,
        source=base_metrics.source,
    )
    baseline_score = base_scores.overall

    # Calculate simulated after-state metrics for this recommendation
    after_metrics = _simulate_metrics_for_recommendations(base_metrics, [rec])
    proj_scores = compute_optimization_scores(
        after_metrics,
        region=after_metrics.region,
        source="SIMULATED",
        is_simulated=True,
        baseline_overall=baseline_score,
    )
    projected_score = proj_scores.overall
    score_delta = projected_score - baseline_score

    resp = await CloudActionDispatcher.execute_recommendation(
        rec=rec,
        dry_run=dry_run,
        simulate=simulate,
        confirm_live=confirm_live,
        resource_id=resource_id,
        target_instance_type=target_instance_type,
        operator_notes=operator_notes,
        provider=provider,
        region=region,
        baseline_score=baseline_score,
        projected_score=projected_score,
        score_delta=score_delta,
        assumptions=proj_scores.assumptions,
    )

    if simulate:
        # User explicitly requested applying to simulated digital twin environment
        rec.status = "simulated"
        rec.applied_at = resp.applied_at
        rec.steps_taken = resp.steps_taken
        if rec.id in state["dismissed"]:
            state["dismissed"].remove(rec.id)
        state["simulated"][rec.id] = resp
        state["score"] = projected_score
        state["simulated_metrics"] = after_metrics
    elif not dry_run and resp.status == "applied":
        # Confirmed live remediation applied and verified on cloud resource
        try:
            await persist_recommendation_state(
                recommendation_id=rec.id,
                provider=provider,
                region=region,
                status="applied",
                applied_at=resp.applied_at,
                steps_taken=resp.steps_taken,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail="The cloud action was confirmed, but recommendation state could not be saved. Check the AWS audit history before retrying.",
            ) from exc

        rec.status = "applied"
        rec.applied_at = resp.applied_at
        rec.steps_taken = resp.steps_taken
        if rec.id in state["dismissed"]:
            state["dismissed"].remove(rec.id)
        state["applied"][rec.id] = resp
        if resp.score_verified and resp.new_score is not None:
            state["score"] = resp.new_score
            state["baseline_score"] = resp.new_score
        # When score is unverified, preserve baseline score rather than claiming projected score
        state["simulated_metrics"] = None

    return resp


@router.get("", response_model=RecommendationsResponse)
async def list_recommendations(
    provider: str = Query("aws"),
    region: str = Query("us-east"),
    refresh: bool = Query(False),
    category: str | None = Query(None),
    priority: str | None = Query(None),
    status: str | None = Query(None),
):
    """Get AI-generated optimization recommendations."""
    from ..database import load_recommendation_states
    state = _user_state(provider, region)

    if refresh or not state["recommendations"]:
        _build_recommendations(provider, region)

    persisted = await load_recommendation_states(provider, region)
    recs = state["recommendations"]
    for rec in recs:
        saved = persisted.get(rec.id)
        if saved and saved["status"] in {"applied", "dismissed"}:
            rec.status = saved["status"]
            rec.applied_at = saved["applied_at"]
            rec.steps_taken = saved["steps_taken"]
            if saved["status"] == "dismissed":
                state["dismissed"].add(rec.id)
            elif saved["status"] == "applied" and rec.id not in state["applied"]:
                state["applied"][rec.id] = ApplyResponse(
                    recommendation_id=rec.id,
                    title=rec.title,
                    status="applied",
                    message="Recorded action status: applied.",
                    estimated_monthly_savings_usd=rec.estimated_monthly_savings_usd,
                    estimated_carbon_reduction_pct=rec.estimated_carbon_reduction_pct,
                    applied_at=saved.get("applied_at") or "",
                    steps_taken=saved.get("steps_taken") or [],
                    dry_run=False,
                    verified=True,
                    verification_status="verified",
                    score_verified=False,
                    provider=provider,
                    region=region,
                )

    if category and category != "all":
        recs = [r for r in recs if r.category == category]
    if priority and priority != "all":
        recs = [r for r in recs if r.priority == priority]
    if status and status != "all":
        recs = [r for r in recs if r.status == status]

    is_simulated = bool(state["simulated"])
    base_score = state.get("baseline_score", state["score"])
    delta = (state["score"] - base_score) if is_simulated else 0

    return RecommendationsResponse(
        recommendations=recs,
        generated_at=state["generated"] or datetime.now(timezone.utc).isoformat(),
        optimization_score=state["score"],
        is_simulated=is_simulated,
        baseline_score=base_score,
        score_delta=delta,
    )


@router.get("/applied", response_model=list[ApplyResponse])
async def list_applied_recommendations(
    provider: str = Query("aws"),
    region: str = Query("us-east"),
):
    """Get audit trail history of all applied recommendations for this user and scope."""
    from ..database import query_audit_log
    _user_state(provider, region)
    audit_entries = await query_audit_log(provider, region)
    applied_list: list[ApplyResponse] = []
    for entry in audit_entries:
        applied_list.append(ApplyResponse(
            recommendation_id=entry.get("recommendation_id", ""),
            title=entry.get("title", ""),
            status=entry.get("status", "applied"),
            message=entry.get("message", "Recorded action status: applied."),
            estimated_monthly_savings_usd=entry.get("estimated_monthly_savings_usd", 0.0),
            estimated_carbon_reduction_pct=entry.get("estimated_carbon_reduction_pct", 0.0),
            applied_at=entry.get("applied_at", ""),
            steps_taken=entry.get("steps_taken", []),
            dry_run=entry.get("dry_run", False),
            new_score=entry.get("new_score"),
            verified=True,
            verification_status="verified",
            provider=provider,
            region=region,
        ))
    state_applied = _user_state(provider, region)["applied"]
    seen_ids = {a.recommendation_id for a in applied_list}
    for rec_id, resp in state_applied.items():
        if rec_id not in seen_ids:
            applied_list.append(resp)
    return applied_list


@router.get("/simulated", response_model=list[ApplyResponse])
def list_simulated_recommendations(
    provider: str = Query("aws"),
    region: str = Query("us-east"),
):
    """Get all recommendations currently applied in the simulated digital twin environment."""
    return list(_user_state(provider, region)["simulated"].values())


@router.post("/reset-simulation")
def reset_simulation(
    provider: str = Query("aws"),
    region: str = Query("us-east"),
):
    """Reset simulated recommendations and restore baseline scores."""
    state = _user_state(provider, region)
    state["simulated"].clear()
    state["simulated_metrics"] = None
    for rec in state["recommendations"]:
        if rec.status == "simulated":
            rec.status = "open"
    base = state.get("baseline_score", 80)
    state["score"] = base
    return {
        "status": "reset",
        "message": "Simulated optimizations reset to baseline telemetry.",
        "baseline_score": base,
        "current_score": base,
    }


@router.post("/apply-batch", response_model=BatchApplyResponse)
async def batch_apply_recommendations(
    req: BatchApplyRequest,
    provider: str = Query("aws"),
    region: str = Query("us-east"),
):
    """Batch apply or preview multiple recommendations simultaneously."""
    state = _user_state(provider, region)

    if not state["recommendations"]:
        _build_recommendations(provider, region)

    targets = [r for r in state["recommendations"] if r.status not in ("applied", "simulated")]

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
        res = await _execute_apply(
            rec,
            dry_run=req.dry_run,
            provider=provider,
            region=region,
        )
        results.append(res)
        total_savings += res.estimated_monthly_savings_usd
        total_carbon += res.estimated_carbon_reduction_pct

    # If dry_run, compute aggregate projected score for all targets
    if req.dry_run and targets and state.get("baseline_metrics"):
        after_all = _simulate_metrics_for_recommendations(state["baseline_metrics"], targets)
        proj = compute_optimization_scores(
            after_all,
            region=state["baseline_metrics"].region,
            source="SIMULATED",
            is_simulated=True,
            baseline_overall=state.get("baseline_score", 80),
        )
        batch_new_score = proj.overall
    else:
        batch_new_score = state["score"]

    return BatchApplyResponse(
        applied_count=sum(result.status == "applied" for result in results),
        total_monthly_savings_usd=round(total_savings, 2),
        total_carbon_reduction_pct=round(total_carbon, 2),
        results=results,
        new_score=batch_new_score,
    )


@router.post("/{rec_id}/apply", response_model=ApplyResponse)
async def apply_recommendation(
    rec_id: str,
    req: ApplyRequest | None = None,
    provider: str = Query("aws"),
    region: str = Query("us-east"),
):
    """Execute remediation action or dry-run preview for a specific recommendation."""
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
    simulate = req.simulate if req else False
    confirm_live = req.confirm_live if req else False
    resource_id = req.resource_id if req else None
    target_instance_type = req.target_instance_type if req else None
    operator_notes = req.operator_notes if req else None
    req_provider = (req.provider if req and req.provider else provider)
    req_region = (req.region if req and req.region else region)

    return await _execute_apply(
        rec,
        dry_run=dry_run,
        simulate=simulate,
        confirm_live=confirm_live,
        resource_id=resource_id,
        target_instance_type=target_instance_type,
        operator_notes=operator_notes,
        provider=req_provider,
        region=req_region,
    )


@router.post("/{rec_id}/simulate", response_model=ApplyResponse)
async def simulate_recommendation(
    rec_id: str,
    req: ApplyRequest | None = None,
    provider: str = Query("aws"),
    region: str = Query("us-east"),
):
    """Simulate applying a recommendation to the digital twin infrastructure model."""
    state = _user_state(provider, region)

    if not state["recommendations"]:
        _build_recommendations(provider, region)

    rec = next((r for r in state["recommendations"] if r.id == rec_id), None)
    if not rec:
        raise HTTPException(
            status_code=404,
            detail=f"Recommendation '{rec_id}' not found.",
        )

    operator_notes = req.operator_notes if req else None
    return await _execute_apply(
        rec,
        dry_run=True,
        simulate=True,
        operator_notes=operator_notes,
        provider=provider,
        region=region,
    )


@router.post("/{rec_id}/rollback", response_model=ApplyResponse)
async def rollback_recommendation(
    rec_id: str,
    provider: str = Query("aws"),
    region: str = Query("us-east"),
    operator_notes: str | None = Query(None),
):
    """Execute rollback for an applied recommendation if prior state is recorded."""
    from ..database import persist_recommendation_state
    state = _user_state(provider, region)
    from ..integrations.cloud_actions import CloudActionDispatcher

    if not state["recommendations"]:
        _build_recommendations(provider, region)

    rec = next((r for r in state["recommendations"] if r.id == rec_id), None)
    if not rec:
        raise HTTPException(
            status_code=404,
            detail=f"Recommendation '{rec_id}' not found.",
        )

    prior_apply = state["applied"].get(rec_id)
    if not prior_apply:
        raise HTTPException(
            status_code=501,
            detail="Cloud remediation rollback is not implemented for this action without a recorded prior state.",
        )

    resp = await CloudActionDispatcher.rollback_recommendation(
        rec=rec,
        operator_notes=operator_notes,
        provider=provider,
        region=region,
        previous_state=prior_apply.previous_state,
        resource_id=prior_apply.resource_id,
    )

    try:
        await persist_recommendation_state(
            recommendation_id=rec.id,
            provider=provider,
            region=region,
            status="open",
        )
    except Exception:
        pass

    rec.status = "open"
    state["applied"].pop(rec_id, None)
    return resp


@router.post("/{rec_id}/dismiss")
async def dismiss_recommendation(
    rec_id: str,
    provider: str = Query("aws"),
    region: str = Query("us-east"),
):
    """Dismiss a recommendation in the selected cloud scope."""
    from ..database import persist_recommendation_state
    state = _user_state(provider, region)

    if not state["recommendations"]:
        _build_recommendations(provider, region)

    rec = next((r for r in state["recommendations"] if r.id == rec_id), None)
    if not rec:
        raise HTTPException(
            status_code=404,
            detail=f"Recommendation '{rec_id}' not found.",
        )

    await persist_recommendation_state(
        recommendation_id=rec.id,
        provider=provider,
        region=region,
        status="dismissed",
    )
    rec.status = "dismissed"
    state["dismissed"].add(rec_id)
    state["applied"].pop(rec_id, None)
    state["simulated"].pop(rec_id, None)
    return {"status": "dismissed", "recommendation_id": rec_id}


@router.get("/{rec_id}/explain", response_model=ExplainResponse)
def explain_recommendation(
    rec_id: str,
    provider: str = Query("aws"),
    region: str = Query("us-east"),
):
    """Explain a recommendation using the metrics and evidence from its scope."""
    state = _user_state(provider, region)
    if not state["recommendations"]:
        _build_recommendations(provider, region)

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
    metrics = state.get("metrics") or state.get("baseline_metrics")
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


def get_recommendations_summary(provider: str = "aws", region: str = "us-east") -> dict[str, Any]:
    """Summary of active recommendations for Copilot and system intelligence."""
    state = _user_state(provider, region)
    if not state["recommendations"]:
        _build_recommendations(provider, region)
    open_recs = [r for r in state["recommendations"] if r.status in ("open", "simulated")]
    total_savings = sum(r.estimated_monthly_savings_usd for r in open_recs)
    return {
        "total_count": len(state["recommendations"]),
        "open_count": len(open_recs),
        "applied_count": len(state["applied"]),
        "simulated_count": len(state["simulated"]),
        "score": state["score"],
        "baseline_score": state.get("baseline_score", state["score"]),
        "total_savings_usd": round(total_savings, 2),
        "top_recommendations": open_recs[:3],
    }
