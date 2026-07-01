from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.knowledge_graph import ExtractionResult, GraphResponse
from app.services.document_context import get_owned_ready_document, load_document_text
from app.services.knowledge_graph.extractor import KnowledgeGraphExtractor
from app.services.knowledge_graph.neo4j_store import get_neo4j_store


class KnowledgeGraphService:
    def __init__(self) -> None:
        self.extractor = KnowledgeGraphExtractor()
        self.store = get_neo4j_store()

    async def build_for_document(
        self, db: AsyncSession, *, document_id: uuid.UUID, user_id: uuid.UUID
    ) -> ExtractionResult:
        document = await get_owned_ready_document(db, document_id, user_id)
        text = await load_document_text(db, document_id, max_chars=18_000)

        entities, relations, tokens = await self.extractor.extract(document.title, text)

        await self.store.ensure_constraints()
        await self.store.upsert_graph(
            user_id=str(user_id),
            document_id=str(document_id),
            title=document.title,
            entities=entities,
            relations=relations,
        )
        return ExtractionResult(
            document_id=document_id,
            entities=entities,
            relations=relations,
            tokens_used=tokens,
        )

    async def get_document_graph(
        self, *, document_id: uuid.UUID, user_id: uuid.UUID
    ) -> GraphResponse:
        return await self.store.get_document_graph(
            user_id=str(user_id), document_id=str(document_id)
        )

    async def get_user_graph(self, *, user_id: uuid.UUID) -> GraphResponse:
        return await self.store.get_user_graph(user_id=str(user_id))
