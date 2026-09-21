"""
Carbon intensity lookup.

DEMO MODE: uses an illustrative hourly carbon-intensity curve per region,
shaped like real grids typically behave (lower overnight when demand is low
and renewable share is often higher; higher during daytime/evening demand
peaks). These are NOT live measurements.

REAL MODE (not yet wired up): swap `get_carbon_intensity()` for a call to a
real grid-carbon API (e.g. Electricity Maps or WattTime), keyed by the same
(region, hour) signature. Nothing else in the decision engine needs to change
-- that's the point of isolating this in one module.
"""

from enum import Enum

# gCO2/kWh, illustrative, 24 values (hour 0-23). Loosely shaped after typical
# publicly reported day/night carbon-intensity swings for grids with a
# meaningful renewable share. Treat these as *demo* numbers, not measurements.
_DEMO_CURVES = {
    "us-east": [
        350, 340, 330, 325, 320, 330, 360, 400, 430, 440, 445, 440,
        430, 425, 430, 440, 450, 460, 470, 460, 440, 410, 380, 360,
    ],
    "in-north": [
        620, 600, 590, 585, 590, 610, 660, 700, 720, 715, 700, 690,
        685, 690, 700, 715, 730, 740, 730, 710, 690, 670, 650, 635,
    ],
}

DEFAULT_REGION = "us-east"


class DataSource(str, Enum):
    DEMO = "DEMO"
    LIVE = "LIVE"


def available_regions() -> list[str]:
    return list(_DEMO_CURVES.keys())


def get_carbon_intensity(region: str, hour: int) -> dict:
    """Returns carbon intensity (gCO2/kWh) for a region at a given hour (0-23)."""
    curve = _DEMO_CURVES.get(region, _DEMO_CURVES[DEFAULT_REGION])
    hour = hour % 24
    return {
        "region": region if region in _DEMO_CURVES else DEFAULT_REGION,
        "hour": hour,
        "carbon_intensity_gco2_per_kwh": curve[hour],
        "source": DataSource.DEMO,
    }


def get_intensity_curve(region: str) -> list[dict]:
    """Full 24h curve for a region -- used by the frontend simulator chart."""
    return [get_carbon_intensity(region, h) for h in range(24)]


def find_greenest_window(region: str, start_hour: int, window_hours: int = 12) -> dict:
    """
    Within the next `window_hours` starting at `start_hour`, find the hour
    with the lowest carbon intensity. Used by the decision engine to suggest
    WHEN to run a deferrable workload.
    """
    candidates = [
        get_carbon_intensity(region, (start_hour + offset) % 24)
        for offset in range(window_hours)
    ]
    best = min(candidates, key=lambda c: c["carbon_intensity_gco2_per_kwh"])
    now = candidates[0]
    reduction_pct = 0.0
    if now["carbon_intensity_gco2_per_kwh"] > 0:
        reduction_pct = 100 * (
            1
            - best["carbon_intensity_gco2_per_kwh"]
            / now["carbon_intensity_gco2_per_kwh"]
        )
    return {
        "current_hour_intensity": now,
        "best_hour_intensity": best,
        "hours_from_now": (best["hour"] - start_hour) % 24,
        "estimated_carbon_reduction_pct": round(reduction_pct, 1),
    }
