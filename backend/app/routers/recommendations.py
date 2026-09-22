"""Recommendations router — AI-generated optimization recommendations."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from .. import carbon
from ..agents import orchestrator
from ..decision_engine import right_size, scaling_advice
from ..routers.telemetry import _generate_live_metrics
from ..schemas import (
    ExplainResponse,
    RecommendationItem,
    RecommendationsResponse,
)

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

# Cache last generated recommendations (in-memory, simple)
_last_recommendations: list[RecommendationItem] = []
_last_score: int = 80
_last_generated: str = ""


def _build_recommendations(provider: str, region: str) -> tuple[list[RecommendationItem], int]:
    metrics = _generate_live_metrics(provider, region)
    result = orchestrator.run(metrics)
    global _last_recommendations, _last_score, _last_generated
    _last_recommendations = result.unified_recommendations
    _last_score = result.overall_score
    _last_generated = datetime.utcnow().isoformat()
    return _last_recommendations, _last_score


@router.get("", response_model=RecommendationsResponse)
def list_recommendations(
    provider: str = Query("aws"),
    region: str = Query("us-east"),
    refresh: bool = Query(False),
    category: str | None = Query(None),
    priority: str | None = Query(None),
):
    """Get AI-generated optimization recommendations."""
    global _last_recommendations, _last_score, _last_generated

    if refresh or not _last_recommendations:
        _build_recommendations(provider, region)

    recs = _last_recommendations
    if category:
        recs = [r for r in recs if r.category == category]
    if priority:
        recs = [r for r in recs if r.priority == priority]

    return RecommendationsResponse(
        recommendations=recs,
        generated_at=_last_generated or datetime.utcnow().isoformat(),
        optimization_score=_last_score,
    )


@router.get("/{rec_id}/explain", response_model=ExplainResponse)
def explain_recommendation(rec_id: str):
    """Get explainability breakdown for a recommendation."""
    rec = next((r for r in _last_recommendations if r.id == rec_id), None)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation '{rec_id}' not found. Run /recommendations first.")

    _EXPLANATIONS = {
        "cost": {
            "why_flagged": "Cost anomaly detected based on utilization-to-spend ratio analysis.",
            "counterfactual": "If current spending patterns continue unchanged, projected monthly overspend will increase.",
        },
        "performance": {
            "why_flagged": "Performance metrics show utilization approaching saturation thresholds.",
            "counterfactual": "Without intervention, latency will increase and SLOs will be breached.",
        },
        "sustainability": {
            "why_flagged": "Carbon intensity analysis shows significant emissions reduction is achievable.",
            "counterfactual": "Maintaining current scheduling pattern misses carbon-free hours.",
        },
        "security": {
            "why_flagged": "Security posture assessment detected configuration against best practices.",
            "counterfactual": "These configurations represent known attack vectors actively exploited.",
        },
        "reliability": {
            "why_flagged": "Reliability assessment identified infrastructure risk factors.",
            "counterfactual": "Without redundancy, a single failure event causes complete service outage.",
        },
    }
    cat_explain = _EXPLANATIONS.get(rec.category, _EXPLANATIONS["cost"])

    return ExplainResponse(
        recommendation_id=rec.id,
        title=rec.title,
        why_flagged=cat_explain["why_flagged"],
        data_evidence=[{"key": e, "value": "Detected"} for e in rec.evidence],
        counterfactual=cat_explain["counterfactual"],
        steps_to_implement=[
            f"Review the {rec.category} dashboard for current state",
            f"Apply action: {rec.action}",
            "Verify impact against baseline after 24h",
            "Update runbook and document the change",
        ],
        expected_outcome=rec.impact_summary,
    )
