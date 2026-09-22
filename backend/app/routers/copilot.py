"""Copilot router — natural language AI assistant endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from ..agents.copilot import respond
from ..schemas import CopilotRequest, CopilotResponse

router = APIRouter(prefix="/copilot", tags=["AI Copilot"])


@router.post("/chat", response_model=CopilotResponse)
async def chat(req: CopilotRequest):
    """Process a natural language message and return a structured Copilot response."""
    history = [{"role": m.role, "content": m.content} for m in req.history]
    result = await respond(req.message, history, req.context)
    return CopilotResponse(
        reply=result["reply"],
        actions=result.get("actions", []),
        charts=result.get("charts", []),
        follow_up_suggestions=result.get("follow_up_suggestions", []),
    )


@router.get("/suggestions")
def suggested_queries():
    """Return suggested starter queries for the Copilot."""
    return {
        "suggestions": [
            "What can I do to reduce my cloud bill?",
            "When is the best time to run my batch job tonight?",
            "What is my overall optimization score?",
            "Am I at risk of an SLO breach?",
            "Which region has the lowest carbon intensity right now?",
            "Simulate what happens if I resize to m5.large",
            "Show me my top 3 security risks",
            "How does my carbon footprint compare to last week?",
        ]
    }
