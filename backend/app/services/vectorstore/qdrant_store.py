from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger
from app.services.vectorstore.base import (
    BaseVectorStore,
    VectorRecord,
    VectorSearchHit,
)

logger = get_logger(__name__)


class QdrantVectorStore(BaseVectorStore):
    """Qdrant-backed vector store with per-user / per-document metadata filtering."""

    def __init__(
        self,
        collection: str | None = None,
        url: str | None = None,
        api_key: str | None = None,
        dim: int | None = None,
    ) -> None:
        from qdrant_client import AsyncQdrantClient

        self.collection = collection or settings.QDRANT_COLLECTION
        self.dim = dim or settings.EMBEDDING_DIM
        self._client = AsyncQdrantClient(
            url=url or settings.QDRANT_URL,
            api_key=api_key or settings.QDRANT_API_KEY,
        )

    async def ensure_collection(self) -> None:
        from qdrant_client import models as qm

        exists = await self._client.collection_exists(self.collection)
        if exists:
            return

        logger.info("creating_qdrant_collection", name=self.collection, dim=self.dim)
        await self._client.create_collection(
            collection_name=self.collection,
            vectors_config=qm.VectorParams(
                size=self.dim, distance=qm.Distance.COSINE
            ),
        )
        # Payload indexes make metadata filtering fast at scale.
        for field_name in ("user_id", "document_id"):
            await self._client.create_payload_index(
                collection_name=self.collection,
                field_name=field_name,
                field_schema=qm.PayloadSchemaType.KEYWORD,
            )

    async def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        from qdrant_client import models as qm

        points = [
            qm.PointStruct(id=r.id, vector=r.vector, payload=r.payload)
            for r in records
        ]
        await self._client.upsert(collection_name=self.collection, points=points)

    async def search(
        self,
        query_vector: list[float],
        *,
        top_k: int = 20,
        user_id: str | None = None,
        document_ids: list[str] | None = None,
    ) -> list[VectorSearchHit]:
        from qdrant_client import models as qm

        must: list = []
        if user_id:
            must.append(
                qm.FieldCondition(key="user_id", match=qm.MatchValue(value=user_id))
            )
        if document_ids:
            must.append(
                qm.FieldCondition(
                    key="document_id",
                    match=qm.MatchAny(any=[str(d) for d in document_ids]),
                )
            )
        query_filter = qm.Filter(must=must) if must else None

        result = await self._client.query_points(
            collection_name=self.collection,
            query=query_vector,
            limit=top_k,
            query_filter=query_filter,
            with_payload=True,
        )
        return [
            VectorSearchHit(id=str(p.id), score=p.score, payload=p.payload or {})
            for p in result.points
        ]

    async def delete_by_document(self, document_id: str) -> None:
        from qdrant_client import models as qm

        await self._client.delete(
            collection_name=self.collection,
            points_selector=qm.FilterSelector(
                filter=qm.Filter(
                    must=[
                        qm.FieldCondition(
                            key="document_id",
                            match=qm.MatchValue(value=str(document_id)),
                        )
                    ]
                )
            ),
        )
