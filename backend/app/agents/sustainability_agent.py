"""
Sustainability Agent — carbon intensity scheduling, green region migration,
and embodied-carbon-aware recommendations.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .. import carbon
from ..schemas import CloudMetrics, RecommendationItem


def analyze(metrics: CloudMetrics, context: dict | None = None) -> dict:
    findings: list[str] = []
    recs: list[RecommendationItem] = []
    score = 100

    region = metrics.region
    carbon_gco2 = metrics.carbon_gco2_per_hour
    cpu = metrics.cpu

    now_dt = datetime.now(timezone.utc)
    current_hour = now_dt.hour

    # ── Carbon intensity of current region ────────────────────────────────────
    intensity = carbon.get_carbon_intensity(region, current_hour)
    ci = intensity["carbon_intensity_gco2_per_kwh"]
    region_score = carbon.region_green_score(region)

    if ci > 500:
        score -= 30
        findings.append(f"Region {region} has very high carbon intensity: {ci:.0f} gCO2/kWh")
    elif ci > 300:
        score -= 15
        findings.append(f"Region {region} has moderate carbon intensity: {ci:.0f} gCO2/kWh")
    else:
        findings.append(f"Region {region} is relatively clean: {ci:.0f} gCO2/kWh")

    # ── Green window scheduling ───────────────────────────────────────────────
    window = carbon.find_greenest_window(region, current_hour, 12)
    hours_away = window["hours_from_now"]
    reduction = window["estimated_carbon_reduction_pct"]

    if hours_away > 0 and reduction > 10 and cpu < 70:
        score -= 20
        findings.append(
            f"Greener window available in {hours_away}h — {reduction:.0f}% carbon reduction possible"
        )
        recs.append(RecommendationItem(
            id="sus-001",
            category="sustainability",
            priority="high",
            title=f"Schedule deferrable workloads in {hours_away}h",
            description=f"Carbon intensity will drop by {reduction:.0f}% in {hours_away}h. "
                        "Batch jobs and non-latency-sensitive workloads should be deferred.",
            impact_summary=f"{reduction:.0f}% carbon reduction with no cost change",
            estimated_monthly_savings_usd=0,
            estimated_carbon_reduction_pct=reduction,
            effort="low",
            action="defer_to_green_window",
            evidence=[
                f"Current intensity: {ci:.0f} gCO2/kWh",
                f"Best window: {window['best_hour_intensity']['carbon_intensity_gco2_per_kwh']:.0f} gCO2/kWh at hour {window['best_hour_intensity']['hour']}",
            ],
            confidence=0.90,
        ))

    # ── Green region migration ─────────────────────────────────────────────────
    all_regions = carbon.available_regions()
    greener = [r for r in all_regions if carbon.region_green_score(r) > region_score + 20]
    if greener:
        best_green = max(greener, key=lambda r: carbon.region_green_score(r))
        best_score = carbon.region_green_score(best_green)
        score -= 15
        findings.append(f"Region {best_green} is significantly greener (score {best_score:.0f} vs {region_score:.0f})")
        recs.append(RecommendationItem(
            id="sus-002",
            category="sustainability",
            priority="medium",
            title=f"Consider migrating to {best_green} for lower carbon footprint",
            description=f"Region {best_green} has a green score of {best_score:.0f}/100 vs {region_score:.0f}/100 for {region}. "
                        "Migrating long-running workloads could significantly reduce Scope 2 emissions.",
            impact_summary=f"Up to {best_score - region_score:.0f} point improvement in green score",
            estimated_monthly_savings_usd=0,
            estimated_carbon_reduction_pct=round((best_score - region_score) / 100 * 60, 1),
            effort="high",
            action="evaluate_region_migration",
            evidence=[
                f"Current region score: {region_score:.0f}/100",
                f"Target region score: {best_score:.0f}/100",
            ],
            confidence=0.75,
        ))

    # ── Carbon budget overage ─────────────────────────────────────────────────
    monthly_carbon_kg = carbon_gco2 * 24 * 30 / 1000
    if monthly_carbon_kg > 100:
        score -= 10
        findings.append(f"Estimated monthly carbon: {monthly_carbon_kg:.0f} kg CO2")
        recs.append(RecommendationItem(
            id="sus-003",
            category="sustainability",
            priority="low",
            title="Set carbon budget alerts and track Scope 2 emissions",
            description=f"Estimated monthly emissions of {monthly_carbon_kg:.0f} kg CO2. "
                        "Establish a carbon budget and configure alerts when thresholds are crossed.",
            impact_summary="Visibility into carbon footprint enables reduction planning",
            estimated_monthly_savings_usd=0,
            estimated_carbon_reduction_pct=0,
            effort="low",
            action="configure_carbon_alerts",
            evidence=[f"Monthly estimate: {monthly_carbon_kg:.0f} kg CO2"],
            confidence=0.85,
        ))

    return {
        "agent": "SustainabilityAgent",
        "status": "completed",
        "findings": findings,
        "recommendations": recs,
        "score": max(0, min(100, score)),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }
