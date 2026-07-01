from __future__ import annotations

import json

from app.core.logging import get_logger
from app.services.llm import get_llm
from app.services.llm.base import LLMMessage

logger = get_logger(__name__)

_EXPANSION_SYSTEM = (
    "You rewrite a user's question about a scientific paper into several search "
    "queries that maximise retrieval recall. Produce diverse paraphrases and "
    "decompositions that surface different keywords and synonyms. "
    "Respond ONLY with JSON: {\"queries\": [\"...\", \"...\"]}."
)


class QueryProcessor:
    """Query understanding + expansion (multi-query retrieval)."""

    def __init__(self, num_expansions: int = 3) -> None:
        self.num_expansions = num_expansions
        self.llm = get_llm()

    async def expand(self, query: str, *, history: str | None = None) -> list[str]:
        """Return [original_query, ...paraphrases]. Falls back to [query] on failure."""
        user = query if not history else f"Conversation so far:\n{history}\n\nQuestion: {query}"
        messages: list[LLMMessage] = [
            {"role": "system", "content": _EXPANSION_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"{user}\n\nGenerate {self.num_expansions} alternative search "
                    "queries."
                ),
            },
        ]
        try:
            resp = await self.llm.complete(
                messages,
                temperature=0.3,
                max_tokens=300,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.content)
            queries = [q.strip() for q in data.get("queries", []) if q.strip()]
        except Exception as exc:  # noqa: BLE001
            logger.warning("query_expansion_failed", error=str(exc))
            queries = []

        # De-dupe while preserving order; always include the original query first.
        seen: set[str] = set()
        result: list[str] = []
        for q in [query, *queries]:
            key = q.lower()
            if key not in seen:
                seen.add(key)
                result.append(q)
        return result[: self.num_expansions + 1]
