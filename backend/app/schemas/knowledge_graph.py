from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class Entity(BaseModel):
    name: str
    type: str = "Concept"  # Concept | Method | Dataset | Task | Metric | Model | Author


class Relation(BaseModel):
    source: str
    relation: str
    target: str


class ExtractionResult(BaseModel):
    document_id: uuid.UUID
    entities: list[Entity] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
    tokens_used: int = 0


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    # Number of papers mentioning it — drives node size in the UI
    weight: int = 1


class GraphEdge(BaseModel):
    source: str
    target: str
    label: str


class GraphResponse(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
