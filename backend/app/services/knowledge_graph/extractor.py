from __future__ import annotations

import json

from app.core.logging import get_logger
from app.schemas.knowledge_graph import Entity, Relation
from app.services.llm.factory import get_heavy_llm
from app.services.llm.base import LLMMessage

logger = get_logger(__name__)

_ENTITY_TYPES = "Concept, Method, Model, Dataset, Task, Metric, Tool, Author"

_SYSTEM = (
    "You are a scientific knowledge-graph extractor. From the paper text, extract the "
    "key entities and the relations between them. Use canonical, de-duplicated names "
    f"(e.g. 'Self-Attention'). Entity types: {_ENTITY_TYPES}. Relations should be short "
    "verb phrases in UPPER_SNAKE_CASE (e.g. USES, PROPOSES, EVALUATES_ON, OUTPERFORMS, "
    "IS_A, PART_OF, TRAINED_ON). Respond ONLY with JSON:\n"
    "{\n"
    '  "entities": [{"name": "...", "type": "..."}],\n'
    '  "relations": [{"source": "...", "relation": "...", "target": "..."}]\n'
    "}\n"
    "Only include relations whose source and target both appear in entities."
)


class KnowledgeGraphExtractor:
    def __init__(self) -> None:
        # Use the heavier model — extraction quality matters a lot here.
        self.llm = get_heavy_llm()

    async def extract(
        self, title: str, text: str
    ) -> tuple[list[Entity], list[Relation], int]:
        messages: list[LLMMessage] = [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": f"Title: {title}\n\nPaper text:\n{text}"},
        ]
        resp = await self.llm.complete(
            messages,
            temperature=0.0,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )
        try:
            data = json.loads(resp.content)
        except json.JSONDecodeError:
            logger.warning("kg_extract_parse_failed")
            return [], [], resp.total_tokens

        entities = _dedupe_entities(data.get("entities", []))
        valid_names = {e.name for e in entities}
        relations = [
            Relation(
                source=r["source"], relation=r.get("relation", "RELATED_TO"), target=r["target"]
            )
            for r in data.get("relations", [])
            if r.get("source") in valid_names and r.get("target") in valid_names
        ]
        return entities, relations, resp.total_tokens


def _dedupe_entities(raw: list[dict]) -> list[Entity]:
    seen: dict[str, Entity] = {}
    for item in raw:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        key = name.lower()
        if key not in seen:
            seen[key] = Entity(name=name, type=(item.get("type") or "Concept").strip())
    return list(seen.values())
