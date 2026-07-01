from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.agent import AgentResponse
from app.services.llm.base import LLMMessage


@dataclass
class AgentContext:
    """Everything an agent needs to act on the user's behalf."""

    db: AsyncSession
    user_id: uuid.UUID
    document_ids: list[uuid.UUID] | None = None
    history: list[LLMMessage] = field(default_factory=list)

    @property
    def document_id_strs(self) -> list[str] | None:
        return [str(d) for d in self.document_ids] if self.document_ids else None


class BaseAgent(ABC):
    name: str

    @abstractmethod
    async def run(self, query: str, ctx: AgentContext) -> AgentResponse: ...
