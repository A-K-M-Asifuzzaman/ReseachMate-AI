from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.chunk import Chunk
from app.models.document import Document
from app.schemas.rag import RetrievedChunk
from app.services.embedding import get_embedder
from app.services.vectorstore import get_vector_store

logger = get_logger(__name__)

_RRF_K = 60  # reciprocal-rank-fusion constant
_BM25_CORPUS_CAP = 5000  # bound in-memory keyword index size
_TOKEN = re.compile(r"[A-Za-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text)]


class HybridRetriever:
    """Dense vector search + BM25 keyword search, fused with RRF."""

    def __init__(self) -> None:
        self.embedder = get_embedder()
        self.vector_store = get_vector_store()

    async def _dense(
        self,
        queries: list[str],
        *,
        user_id: str,
        document_ids: list[str] | None,
        top_k: int,
    ) -> dict[str, float]:
        """Return {chunk_id: best_dense_score} across all expanded queries."""
        vectors = self.embedder.embed_queries(queries)
        best: dict[str, float] = {}
        for vec in vectors:
            hits = await self.vector_store.search(
                vec, top_k=top_k, user_id=user_id, document_ids=document_ids
            )
            for hit in hits:
                if hit.score > best.get(hit.id, -1.0):
                    best[hit.id] = hit.score
        return best

    async def _keyword(
        self,
        query: str,
        *,
        db: AsyncSession,
        user_id: str,
        document_ids: list[str] | None,
        top_k: int,
    ) -> dict[str, float]:
        """BM25 over the candidate chunk pool from Postgres."""
        from rank_bm25 import BM25Okapi

        stmt = select(Chunk).where(Chunk.user_id == uuid.UUID(user_id))
        if document_ids:
            stmt = stmt.where(
                Chunk.document_id.in_([uuid.UUID(d) for d in document_ids])
            )
        stmt = stmt.limit(_BM25_CORPUS_CAP)
        rows = (await db.execute(stmt)).scalars().all()
        if not rows:
            return {}

        corpus = [_tokenize(c.content) for c in rows]
        bm25 = BM25Okapi(corpus)
        scores = bm25.get_scores(_tokenize(query))

        ranked = sorted(
            zip(rows, scores), key=lambda x: x[1], reverse=True
        )[:top_k]
        return {str(row.id): float(score) for row, score in ranked if score > 0}

    @staticmethod
    def _rrf(ranked_ids: list[str]) -> dict[str, float]:
        return {cid: 1.0 / (_RRF_K + rank) for rank, cid in enumerate(ranked_ids)}

    async def retrieve(
        self,
        query: str,
        expanded_queries: list[str],
        *,
        db: AsyncSession,
        user_id: str,
        document_ids: list[str] | None = None,
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        top_k = top_k or settings.RETRIEVAL_TOP_K

        dense_scores = await self._dense(
            expanded_queries, user_id=user_id, document_ids=document_ids, top_k=top_k
        )
        keyword_scores = await self._keyword(
            query, db=db, user_id=user_id, document_ids=document_ids, top_k=top_k
        )

        # Reciprocal-rank fusion of the two ranked lists.
        dense_ranked = sorted(dense_scores, key=dense_scores.get, reverse=True)  # type: ignore[arg-type]
        keyword_ranked = sorted(keyword_scores, key=keyword_scores.get, reverse=True)  # type: ignore[arg-type]
        dense_rrf = self._rrf(dense_ranked)
        keyword_rrf = self._rrf(keyword_ranked)

        fused: dict[str, float] = {}
        for cid in set(dense_rrf) | set(keyword_rrf):
            fused[cid] = dense_rrf.get(cid, 0.0) + keyword_rrf.get(cid, 0.0)

        top_ids = sorted(fused, key=fused.get, reverse=True)[:top_k]  # type: ignore[arg-type]
        if not top_ids:
            return []

        return await self._hydrate(
            top_ids,
            db=db,
            dense_scores=dense_scores,
            keyword_scores=keyword_scores,
            fused=fused,
        )

    async def _hydrate(
        self,
        chunk_ids: list[str],
        *,
        db: AsyncSession,
        dense_scores: dict[str, float],
        keyword_scores: dict[str, float],
        fused: dict[str, float],
    ) -> list[RetrievedChunk]:
        """Load chunk + document metadata from Postgres to build citations."""
        uuids = [uuid.UUID(c) for c in chunk_ids]
        rows = (
            await db.execute(select(Chunk).where(Chunk.id.in_(uuids)))
        ).scalars().all()
        doc_ids = {r.document_id for r in rows}
        docs = (
            await db.execute(select(Document).where(Document.id.in_(doc_ids)))
        ).scalars().all()
        doc_map = {d.id: d for d in docs}

        by_id = {str(r.id): r for r in rows}
        results: list[RetrievedChunk] = []
        for cid in chunk_ids:  # preserve fused ranking order
            row = by_id.get(cid)
            if row is None:
                continue
            doc = doc_map.get(row.document_id)
            results.append(
                RetrievedChunk(
                    chunk_id=row.id,
                    document_id=row.document_id,
                    content=row.content,
                    title=doc.title if doc else "Unknown",
                    authors=doc.authors if doc else None,
                    page_number=row.page_number,
                    section=row.section,
                    dense_score=dense_scores.get(cid, 0.0),
                    keyword_score=keyword_scores.get(cid, 0.0),
                    fused_score=fused.get(cid, 0.0),
                )
            )
        return results
