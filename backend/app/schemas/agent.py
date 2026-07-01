from __future__ import annotations

import uuid
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.rag import Citation


class AgentType(str, Enum):
    RESEARCH = "research"
    SUMMARY = "summary"
    CITATION = "citation"
    COMPARISON = "comparison"


class AgentRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    document_ids: list[uuid.UUID] | None = None
    conversation_id: uuid.UUID | None = None
    # Force a specific agent; if None the planner decides.
    agent: AgentType | None = None


class AgentStep(BaseModel):
    name: str
    detail: str


class AgentResponse(BaseModel):
    agent: AgentType
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    steps: list[AgentStep] = Field(default_factory=list)
    tokens_used: int = 0
