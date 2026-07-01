from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

_DEFAULT_DIMENSIONS = [
    "Objective",
    "Dataset",
    "Architecture",
    "Results",
    "Advantages",
    "Limitations",
]


class ComparisonRequest(BaseModel):
    document_ids: list[uuid.UUID] = Field(min_length=2, max_length=5)
    dimensions: list[str] = Field(default_factory=lambda: list(_DEFAULT_DIMENSIONS))


class PaperRef(BaseModel):
    document_id: uuid.UUID
    title: str


class ComparisonRow(BaseModel):
    dimension: str
    # Maps a document_id (as str) -> comparison text for that paper
    cells: dict[str, str]


class ComparisonResponse(BaseModel):
    papers: list[PaperRef]
    rows: list[ComparisonRow]
    synthesis: str
    tokens_used: int = 0
