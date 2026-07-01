"""Helpers to assemble a document's text from its stored chunks.

Used by summarization, comparison, and knowledge-graph extraction — all of which need
the document body but with a bounded token/char budget for the LLM.
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.models.document import Document, DocumentStatus

_DEFAULT_BUDGET = 24_000  # ~6k tokens of context


async def get_owned_ready_document(
    db: AsyncSession, document_id: uuid.UUID, user_id: uuid.UUID
) -> Document:
    document = await db.get(Document, document_id)
    if document is None or document.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found."
        )
    if document.status != DocumentStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document is not ready (status: {document.status.value}).",
        )
    return document


async def load_document_text(
    db: AsyncSession, document_id: uuid.UUID, *, max_chars: int = _DEFAULT_BUDGET
) -> str:
    """Concatenate chunks in reading order up to a character budget."""
    stmt = (
        select(Chunk)
        .where(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index)
    )
    rows = (await db.execute(stmt)).scalars().all()

    parts: list[str] = []
    total = 0
    for chunk in rows:
        header = f"\n[p.{chunk.page_number} · {chunk.section}]\n" if chunk.section else "\n"
        piece = header + chunk.content
        if total + len(piece) > max_chars:
            remaining = max_chars - total
            if remaining > 200:
                parts.append(piece[:remaining])
            break
        parts.append(piece)
        total += len(piece)
    return "".join(parts).strip()
