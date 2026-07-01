from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.chat import MessageRole


class ConversationCreate(BaseModel):
    title: str | None = None
    document_ids: list[uuid.UUID] = Field(default_factory=list)


class MessagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: MessageRole
    content: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime


class ConversationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    document_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationPublic):
    messages: list[MessagePublic] = Field(default_factory=list)


class ConversationListResponse(BaseModel):
    items: list[ConversationPublic]
    total: int
