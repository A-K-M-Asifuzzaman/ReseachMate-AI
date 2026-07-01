from __future__ import annotations

import json

from app.core.logging import get_logger
from app.schemas.summary import DetailedSummary
from app.services.llm import get_llm
from app.services.llm.base import LLMMessage

logger = get_logger(__name__)

_SHORT_SYSTEM = (
    "You are a scientific summarizer. Write a faithful 5-10 line summary of the paper "
    "below in plain language. Cover what problem it solves, the core idea, and the main "
    "result. Do not invent details not present in the text."
)

_DETAILED_SYSTEM = (
    "You are a scientific summarizer. Read the paper text and produce a structured "
    "summary. Respond ONLY with JSON matching this schema, each value a concise "
    "paragraph grounded in the text (empty string if genuinely absent):\n"
    "{\n"
    '  "problem": "the problem/motivation",\n'
    '  "methodology": "approach and methods",\n'
    '  "dataset": "datasets/benchmarks used",\n'
    '  "model": "model/architecture details",\n'
    '  "results": "key quantitative and qualitative results",\n'
    '  "limitations": "stated or evident limitations"\n'
    "}"
)


class Summarizer:
    def __init__(self) -> None:
        self.llm = get_llm()

    async def short(self, title: str, text: str) -> tuple[str, int]:
        messages: list[LLMMessage] = [
            {"role": "system", "content": _SHORT_SYSTEM},
            {"role": "user", "content": f"Title: {title}\n\nPaper text:\n{text}"},
        ]
        resp = await self.llm.complete(messages, temperature=0.2, max_tokens=400)
        return resp.content.strip(), resp.total_tokens

    async def detailed(self, title: str, text: str) -> tuple[DetailedSummary, int]:
        messages: list[LLMMessage] = [
            {"role": "system", "content": _DETAILED_SYSTEM},
            {"role": "user", "content": f"Title: {title}\n\nPaper text:\n{text}"},
        ]
        resp = await self.llm.complete(
            messages,
            temperature=0.2,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )
        try:
            data = json.loads(resp.content)
        except json.JSONDecodeError:
            logger.warning("detailed_summary_parse_failed")
            data = {}
        return DetailedSummary(**{k: data.get(k, "") for k in DetailedSummary.model_fields}), resp.total_tokens
