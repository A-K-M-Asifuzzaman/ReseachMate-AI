from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """A single grounded source attached to an answer."""

    document_id: uuid.UUID
    chunk_id: uuid.UUID
    title: str
    authors: str | None = None
    page_number: int | None = None
    section: str | None = None
    snippet: str
    score: float = Field(description="Relevance score after reranking")


class RetrievedChunk(BaseModel):
    """Internal retrieval result passed through the pipeline stages."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    title: str
    authors: str | None = None
    page_number: int | None = None
    section: str | None = None
    dense_score: float = 0.0
    keyword_score: float = 0.0
    fused_score: float = 0.0
    rerank_score: float = 0.0


class RAGQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    document_ids: list[uuid.UUID] | None = Field(
        default=None, description="Restrict retrieval to these documents (None = all)"
    )
    conversation_id: uuid.UUID | None = None
    top_k: int | None = Field(default=None, ge=1, le=50)
    rerank_top_n: int | None = Field(default=None, ge=1, le=20)
    stream: bool = False


class RAGAnswer(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    conversation_id: uuid.UUID | None = None
    query: str
    expanded_queries: list[str] = Field(default_factory=list)
    latency_ms: int | None = None
    tokens_used: int | None = None
