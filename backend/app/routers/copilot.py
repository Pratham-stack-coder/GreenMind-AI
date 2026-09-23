"""Copilot router — natural language AI cloud management assistant endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from ..copilot.agent import copilot_agent
from ..copilot.schemas import CopilotChatRequest
from ..schemas import CopilotRequest, CopilotResponse

router = APIRouter(prefix="/copilot", tags=["AI Copilot"])


@router.post("/chat", response_model=CopilotResponse)
async def chat(req: CopilotRequest):
    """
    Process a natural language message and return a structured Copilot response
    grounded in live cloud telemetry and tool execution.
    """
    history = [{"role": m.role, "content": m.content} for m in req.history]
    internal_req = CopilotChatRequest(
        message=req.message,
        history=history,
        context=req.context or {},
    )
    result = copilot_agent.process_message(internal_req)

    return CopilotResponse(
        reply=result.answer,
        answer=result.answer,
        sources=result.sources,
        actions=[a.model_dump() for a in result.actions],
        charts=[],
        follow_up_suggestions=result.follow_up_suggestions,
        data_snapshot=result.data_snapshot,
    )


@router.get("/suggestions")
def suggested_queries():
    """Return suggested starter queries for the Copilot."""
    return {
        "suggestions": [
            "Why is my cloud cost high?",
            "Should I scale my EC2 instance?",
            "How can I reduce carbon emissions?",
            "What is my current cloud health?",
            "What resources are underutilized?",
            "What happens if I right-size this instance?",
            "When is the best time to run my batch job tonight?",
            "Simulate what happens if I resize to m5.large",
        ]
    }
