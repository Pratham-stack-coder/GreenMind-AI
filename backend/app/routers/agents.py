"""Agents router — trigger multi-agent analysis and retrieve results."""

from __future__ import annotations

from fastapi import APIRouter

from ..agents import orchestrator
from ..routers.telemetry import _generate_live_metrics
from ..schemas import AgentRunRequest, AgentRunResponse

router = APIRouter(prefix="/agents", tags=["Multi-Agent AI"])

_last_run: AgentRunResponse | None = None


@router.post("/run", response_model=AgentRunResponse)
def run_agents(req: AgentRunRequest):
    """Trigger a full multi-agent analysis run."""
    global _last_run
    metrics = req.metrics or _generate_live_metrics(req.provider, req.region)
    context = {
        "open_security_group_ports": ["0.0.0.0/0:22"],
        "unencrypted_volumes": 0,
        "admin_users_without_mfa": 1,
        "availability_zones": 1,
        "has_autoscaling": False,
        "has_backup_policy": False,
        "last_backup_age_hours": 30,
        "has_health_checks": True,
    }
    result = orchestrator.run(metrics, context)
    _last_run = result
    return result


@router.get("/status", response_model=AgentRunResponse | None)
def agent_status():
    """Return the results of the last agent run."""
    return _last_run
