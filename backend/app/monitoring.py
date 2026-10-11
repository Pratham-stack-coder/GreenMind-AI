"""
Prometheus Monitoring for GreenMind AI.
Exposes real-time operational telemetry at /metrics/prometheus.
Tracks request counts, latencies, prediction calls, errors, cloud collections, and agent runs.
"""

from __future__ import annotations

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# In-memory metrics tracking
_API_REQUESTS: dict[tuple[str, str, int], int] = {}
_API_LATENCY_SUM: dict[str, float] = {}
_API_LATENCY_COUNT: dict[str, int] = {}
_PREDICTION_REQUESTS = 0
_API_ERRORS = 0
_CLOUD_COLLECTIONS = 0
_AGENT_EXEC_SUM = 0.0
_AGENT_EXEC_COUNT = 0


def track_prediction_request() -> None:
    global _PREDICTION_REQUESTS
    _PREDICTION_REQUESTS += 1


def track_cloud_collection() -> None:
    global _CLOUD_COLLECTIONS
    _CLOUD_COLLECTIONS += 1


def track_agent_execution(duration_sec: float) -> None:
    global _AGENT_EXEC_SUM, _AGENT_EXEC_COUNT
    _AGENT_EXEC_SUM += duration_sec
    _AGENT_EXEC_COUNT += 1


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        global _API_ERRORS
        start_time = time.time()
        path = request.url.path
        method = request.method

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            _API_ERRORS += 1
            status_code = 500
            raise
        finally:
            duration = time.time() - start_time
            # Increment request counter
            key = (method, path, status_code)
            _API_REQUESTS[key] = _API_REQUESTS.get(key, 0) + 1

            # Track latency
            _API_LATENCY_SUM[path] = _API_LATENCY_SUM.get(path, 0.0) + duration
            _API_LATENCY_COUNT[path] = _API_LATENCY_COUNT.get(path, 0) + 1

            if status_code >= 400:
                _API_ERRORS += 1

        return response


def generate_prometheus_metrics() -> str:
    """Formats tracked metrics into the standard Prometheus text format."""
    lines = [
        "# HELP greenmind_api_requests_total Total number of HTTP requests processed.",
        "# TYPE greenmind_api_requests_total counter",
    ]
    for (method, path, status), count in _API_REQUESTS.items():
        lines.append(f'greenmind_api_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}')

    lines.extend([
        "# HELP greenmind_api_request_duration_seconds Total request latency.",
        "# TYPE greenmind_api_request_duration_seconds summary",
    ])
    for path, sum_sec in _API_LATENCY_SUM.items():
        count = _API_LATENCY_COUNT.get(path, 1)
        lines.append(f'greenmind_api_request_duration_seconds_sum{{path="{path}"}} {sum_sec:.4f}')
        lines.append(f'greenmind_api_request_duration_seconds_count{{path="{path}"}} {count}')

    lines.extend([
        "# HELP greenmind_prediction_requests_total Total ML prediction invocations.",
        "# TYPE greenmind_prediction_requests_total counter",
        f"greenmind_prediction_requests_total {_PREDICTION_REQUESTS}",
        "# HELP greenmind_api_errors_total Total errors encountered.",
        "# TYPE greenmind_api_errors_total counter",
        f"greenmind_api_errors_total {_API_ERRORS}",
        "# HELP greenmind_cloud_collections_total Total telemetry collections.",
        "# TYPE greenmind_cloud_collections_total counter",
        f"greenmind_cloud_collections_total {_CLOUD_COLLECTIONS}",
        "# HELP greenmind_agent_execution_seconds_total Total duration of agent orchestration.",
        "# TYPE greenmind_agent_execution_seconds_total summary",
        f"greenmind_agent_execution_seconds_sum {_AGENT_EXEC_SUM:.4f}",
        f"greenmind_agent_execution_seconds_count {_AGENT_EXEC_COUNT}",
    ])

    # Cloud Operational Gauges
    try:
        from .database import get_telemetry_history
        from .routers.recommendations import get_recommendations_summary
        recent = get_telemetry_history(1)
        rec_summary = get_recommendations_summary()
        t = recent[0] if recent else {}
        cpu = float(t.get("cpu", 48.5))
        cost = float(t.get("cost_usd_per_hour", t.get("cost_per_hour", 0.22)))
        carbon = float(t.get("carbon_gco2_per_hour", t.get("carbon_intensity", 310.0)))
        score = float(rec_summary.get("score", 82))
        open_count = float(rec_summary.get("open_count", 3))
        applied_count = float(rec_summary.get("applied_count", 0))

        lines.extend([
            "# HELP greenmind_cpu_utilization_percent Current CPU utilization percentage.",
            "# TYPE greenmind_cpu_utilization_percent gauge",
            f'greenmind_cpu_utilization_percent{{provider="{t.get("provider", "aws")}",region="{t.get("region", "us-east")}"}} {cpu:.2f}',
            "# HELP greenmind_hourly_cost_usd Estimated cloud infrastructure cost in USD per hour.",
            "# TYPE greenmind_hourly_cost_usd gauge",
            f'greenmind_hourly_cost_usd{{provider="{t.get("provider", "aws")}",region="{t.get("region", "us-east")}"}} {cost:.4f}',
            "# HELP greenmind_carbon_intensity_gco2 Regional grid carbon intensity in gCO2 per kWh.",
            "# TYPE greenmind_carbon_intensity_gco2 gauge",
            f'greenmind_carbon_intensity_gco2{{region="{t.get("region", "us-east")}"}} {carbon:.2f}',
            "# HELP greenmind_optimization_score System overall cloud optimization score (0-100).",
            "# TYPE greenmind_optimization_score gauge",
            f"greenmind_optimization_score {score:.1f}",
            "# HELP greenmind_recommendations_count Active cloud optimization recommendations count.",
            "# TYPE greenmind_recommendations_count gauge",
            f'greenmind_recommendations_count{{status="open"}} {open_count:.1f}',
            f'greenmind_recommendations_count{{status="applied"}} {applied_count:.1f}',
        ])
    except Exception:
        pass

    return "\n".join(lines) + "\n"
