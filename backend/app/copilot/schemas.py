"""
Copilot Schemas for GreenMind AI.
Request and response models for interactive AI Cloud Copilot.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class CopilotAction(BaseModel):
    label: str
    endpoint: str
    method: str = "POST"
    payload: dict[str, Any] = Field(default_factory=dict)


class CopilotChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = Field(default_factory=list)
    provider: str = "aws"
    region: str = "us-east"
    context: dict[str, Any] = Field(default_factory=dict)


class CopilotChatResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    actions: list[CopilotAction] = Field(default_factory=list)
    follow_up_suggestions: list[str] = Field(default_factory=list)
    data_snapshot: dict[str, Any] = Field(default_factory=dict)
