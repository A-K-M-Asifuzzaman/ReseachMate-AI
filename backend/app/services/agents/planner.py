from __future__ import annotations

import json

from app.core.logging import get_logger
from app.schemas.agent import AgentType
from app.services.llm import get_llm
from app.services.llm.base import LLMMessage

logger = get_logger(__name__)

_SYSTEM = (
    "You are a router that picks the best agent for a user's research request.\n"
    "Agents:\n"
    "- research: answer a question about the paper(s) with retrieval + citations.\n"
    "- summary: summarize a single paper.\n"
    "- citation: find and list the exact sources/passages backing a claim.\n"
    "- comparison: compare two or more papers.\n"
    "Respond ONLY with JSON: {\"agent\": \"research|summary|citation|comparison\", "
    "\"reason\": \"<short>\"}."
)


class Planner:
    def __init__(self) -> None:
        self.llm = get_llm()

    async def plan(
        self, query: str, *, num_documents: int
    ) -> tuple[AgentType, str]:
        # Strong heuristic first: comparison is obvious when multiple docs are scoped.
        messages: list[LLMMessage] = [
            {"role": "system", "content": _SYSTEM},
            {
                "role": "user",
                "content": f"Documents in scope: {num_documents}\nRequest: {query}",
            },
        ]
        try:
            resp = await self.llm.complete(
                messages,
                temperature=0.0,
                max_tokens=120,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.content)
            agent = AgentType(data["agent"])
            reason = data.get("reason", "")
        except Exception as exc:  # noqa: BLE001
            logger.warning("planner_failed", error=str(exc))
            agent, reason = AgentType.RESEARCH, "fallback: default research agent"
        return agent, reason
