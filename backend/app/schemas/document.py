from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.document import DocumentStatus


class DocumentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    authors: str | None = None
    year: int | None = None
    journal: str | None = None
    abstract: str | None = None
    filename: str
    file_size: int | None = None
    num_pages: int | None = None
    num_chunks: int
    status: DocumentStatus
    error: str | None = None
    doc_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class DocumentUpdate(BaseModel):
    title: str | None = None
    authors: str | None = None
    year: int | None = None
    journal: str | None = None


class DocumentListResponse(BaseModel):
    items: list[DocumentPublic]
    total: int


class ChunkPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    content: str
    page_number: int | None = None
    section: str | None = None
