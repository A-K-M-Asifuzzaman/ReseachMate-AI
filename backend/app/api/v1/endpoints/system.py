from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession
from app.core.metrics import metrics
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.chat import Conversation

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/stats")
async def user_stats(current_user: CurrentUser, db: DbSession) -> dict:
    """Per-user counts for the dashboard."""

    async def count(model, *conds) -> int:
        stmt = select(func.count()).select_from(model).where(*conds)
        return (await db.execute(stmt)).scalar_one()

    return {
        "documents": await count(Document, Document.user_id == current_user.id),
        "chunks": await count(Chunk, Chunk.user_id == current_user.id),
        "conversations": await count(
            Conversation, Conversation.user_id == current_user.id
        ),
    }


@router.get("/metrics")
async def system_metrics(current_user: CurrentUser) -> dict:
    """Process-wide RAG metrics: latency, tokens, answer success rate."""
    return metrics.snapshot()
