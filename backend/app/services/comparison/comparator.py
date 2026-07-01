from __future__ import annotations

import json
import string

from app.core.logging import get_logger
from app.schemas.comparison import ComparisonRow
from app.services.llm import get_llm
from app.services.llm.base import LLMMessage

logger = get_logger(__name__)

_SYSTEM = (
    "You are a research analyst comparing scientific papers. For each requested "
    "dimension, compare the papers faithfully and concisely, using ONLY the provided "
    "text. Papers are labelled A, B, C… Respond ONLY with JSON:\n"
    "{\n"
    '  "rows": [{"dimension": "<name>", "cells": {"A": "<text>", "B": "<text>"}}],\n'
    '  "synthesis": "<2-4 sentence overall comparison and recommendation>"\n'
    "}"
)


class PaperComparator:
    def __init__(self) -> None:
        self.llm = get_llm()

    async def compare(
        self,
        papers: list[dict],  # [{"document_id", "title", "text"}]
        dimensions: list[str],
    ) -> tuple[list[ComparisonRow], str, int]:
        # Assign stable labels A, B, C… and remember the mapping back to ids.
        labels = list(string.ascii_uppercase)
        label_to_id = {labels[i]: str(p["document_id"]) for i, p in enumerate(papers)}

        blocks = []
        for i, p in enumerate(papers):
            blocks.append(
                f"=== Paper {labels[i]}: {p['title']} ===\n{p['text']}"
            )
        corpus = "\n\n".join(blocks)
        dims = ", ".join(dimensions)

        messages: list[LLMMessage] = [
            {"role": "system", "content": _SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Compare the papers on these dimensions: {dims}.\n\n{corpus}"
                ),
            },
        ]
        resp = await self.llm.complete(
            messages,
            temperature=0.2,
            max_tokens=1800,
            response_format={"type": "json_object"},
        )
        try:
            data = json.loads(resp.content)
        except json.JSONDecodeError:
            logger.warning("comparison_parse_failed")
            data = {"rows": [], "synthesis": ""}

        rows: list[ComparisonRow] = []
        for raw in data.get("rows", []):
            cells_by_id = {
                label_to_id[label]: text
                for label, text in raw.get("cells", {}).items()
                if label in label_to_id
            }
            rows.append(
                ComparisonRow(dimension=raw.get("dimension", ""), cells=cells_by_id)
            )
        return rows, data.get("synthesis", ""), resp.total_tokens
