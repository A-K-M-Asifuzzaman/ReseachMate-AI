from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.comparison import ComparisonRequest, ComparisonResponse, PaperRef
from app.services.comparison import PaperComparator
from app.services.document_context import get_owned_ready_document, load_document_text

router = APIRouter(prefix="/comparison", tags=["comparison"])

# Smaller per-paper budget so several papers fit in one context window.
_PER_PAPER_CHARS = 9_000
_comparator: PaperComparator | None = None


def _get_comparator() -> PaperComparator:
    global _comparator
    if _comparator is None:
        _comparator = PaperComparator()
    return _comparator


@router.post("", response_model=ComparisonResponse)
async def compare_papers(
    payload: ComparisonRequest, current_user: CurrentUser, db: DbSession
) -> ComparisonResponse:
    papers = []
    refs = []
    for doc_id in payload.document_ids:
        document = await get_owned_ready_document(db, doc_id, current_user.id)
        text = await load_document_text(db, doc_id, max_chars=_PER_PAPER_CHARS)
        papers.append({"document_id": doc_id, "title": document.title, "text": text})
        refs.append(PaperRef(document_id=doc_id, title=document.title))

    rows, synthesis, tokens = await _get_comparator().compare(
        papers, payload.dimensions
    )
    return ComparisonResponse(
        papers=refs, rows=rows, synthesis=synthesis, tokens_used=tokens
    )
