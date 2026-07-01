from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.knowledge_graph import ExtractionResult, GraphResponse
from app.services.knowledge_graph import KnowledgeGraphService

router = APIRouter(prefix="/knowledge-graph", tags=["knowledge-graph"])

_service: KnowledgeGraphService | None = None


def _get_service() -> KnowledgeGraphService:
    global _service
    if _service is None:
        _service = KnowledgeGraphService()
    return _service


@router.post("/documents/{document_id}/extract", response_model=ExtractionResult)
async def extract_graph(
    document_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> ExtractionResult:
    """Extract entities/relations for a paper and store them in Neo4j."""
    return await _get_service().build_for_document(
        db, document_id=document_id, user_id=current_user.id
    )


@router.get("/documents/{document_id}", response_model=GraphResponse)
async def document_graph(
    document_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> GraphResponse:
    return await _get_service().get_document_graph(
        document_id=document_id, user_id=current_user.id
    )


@router.get("", response_model=GraphResponse)
async def user_graph(current_user: CurrentUser) -> GraphResponse:
    """The user's whole knowledge graph across all their papers."""
    return await _get_service().get_user_graph(user_id=current_user.id)
