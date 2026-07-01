from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.summary import SummaryRequest, SummaryResponse, SummaryType
from app.services.document_context import get_owned_ready_document, load_document_text
from app.services.summarization import Summarizer

router = APIRouter(prefix="/documents", tags=["summaries"])

_summarizer: Summarizer | None = None


def _get_summarizer() -> Summarizer:
    global _summarizer
    if _summarizer is None:
        _summarizer = Summarizer()
    return _summarizer


@router.post("/{document_id}/summary", response_model=SummaryResponse)
async def summarize_document(
    document_id: uuid.UUID,
    payload: SummaryRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> SummaryResponse:
    document = await get_owned_ready_document(db, document_id, current_user.id)
    text = await load_document_text(db, document_id)
    summarizer = _get_summarizer()

    if payload.summary_type == SummaryType.SHORT:
        short, tokens = await summarizer.short(document.title, text)
        return SummaryResponse(
            document_id=document_id,
            summary_type=SummaryType.SHORT,
            short_summary=short,
            tokens_used=tokens,
        )

    detailed, tokens = await summarizer.detailed(document.title, text)
    return SummaryResponse(
        document_id=document_id,
        summary_type=SummaryType.DETAILED,
        detailed_summary=detailed,
        tokens_used=tokens,
    )
