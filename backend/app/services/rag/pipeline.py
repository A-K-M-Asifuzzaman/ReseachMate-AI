from __future__ import annotations

import asyncio
import time
import uuid
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.rag import RAGAnswer, RetrievedChunk
from app.services.llm.base import LLMMessage
from app.services.rag.generator import AnswerGenerator, build_citations
from app.services.rag.query_processor import QueryProcessor
from app.services.rag.reranker import get_reranker
from app.services.rag.retriever import HybridRetriever

logger = get_logger(__name__)

_NO_CONTEXT_MSG = (
    "I couldn't find anything relevant in your uploaded documents to answer that. "
    "Try rephrasing, or make sure the relevant paper has finished processing."
)


class RAGPipeline:
    """End-to-end retrieval-augmented generation with citations."""

    def __init__(self) -> None:
        self.query_processor = QueryProcessor()
        self.retriever = HybridRetriever()
        self.reranker = get_reranker()
        self.generator = AnswerGenerator()

    async def _retrieve_and_rerank(
        self,
        query: str,
        *,
        db: AsyncSession,
        user_id: str,
        document_ids: list[str] | None,
        history_text: str | None,
        top_k: int | None,
        rerank_top_n: int | None,
    ) -> tuple[list[str], list[RetrievedChunk]]:
        expanded = await self.query_processor.expand(query, history=history_text)
        candidates = await self.retriever.retrieve(
            query,
            expanded,
            db=db,
            user_id=user_id,
            document_ids=document_ids,
            top_k=top_k,
        )
        if not candidates:
            return expanded, []
        reranked = await asyncio.to_thread(
            self.reranker.rerank, query, candidates, rerank_top_n or settings.RERANK_TOP_N
        )
        return expanded, reranked

    async def run(
        self,
        query: str,
        *,
        db: AsyncSession,
        user_id: str | uuid.UUID,
        document_ids: list[str] | None = None,
        history: list[LLMMessage] | None = None,
        top_k: int | None = None,
        rerank_top_n: int | None = None,
    ) -> RAGAnswer:
        started = time.perf_counter()
        history_text = _history_to_text(history)

        expanded, chunks = await self._retrieve_and_rerank(
            query,
            db=db,
            user_id=str(user_id),
            document_ids=document_ids,
            history_text=history_text,
            top_k=top_k,
            rerank_top_n=rerank_top_n,
        )

        if not chunks:
            return RAGAnswer(
                answer=_NO_CONTEXT_MSG,
                citations=[],
                query=query,
                expanded_queries=expanded,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )

        answer, citations, tokens = await self.generator.generate(query, chunks, history)
        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "rag_answered",
            user_id=str(user_id),
            chunks=len(chunks),
            tokens=tokens,
            latency_ms=latency_ms,
        )
        return RAGAnswer(
            answer=answer,
            citations=citations,
            query=query,
            expanded_queries=expanded,
            latency_ms=latency_ms,
            tokens_used=tokens,
        )

    async def run_stream(
        self,
        query: str,
        *,
        db: AsyncSession,
        user_id: str | uuid.UUID,
        document_ids: list[str] | None = None,
        history: list[LLMMessage] | None = None,
        top_k: int | None = None,
        rerank_top_n: int | None = None,
    ) -> AsyncIterator[dict]:
        """Yield streaming events: expanded → token* → citations → done.

        Citations are emitted up front (all reranked passages), since we can't parse
        inline references until generation completes; the client renders them alongside
        the streamed answer.
        """
        history_text = _history_to_text(history)
        expanded, chunks = await self._retrieve_and_rerank(
            query,
            db=db,
            user_id=str(user_id),
            document_ids=document_ids,
            history_text=history_text,
            top_k=top_k,
            rerank_top_n=rerank_top_n,
        )
        yield {"type": "expanded", "queries": expanded}

        if not chunks:
            yield {"type": "token", "text": _NO_CONTEXT_MSG}
            yield {"type": "citations", "citations": []}
            yield {"type": "done", "answer": _NO_CONTEXT_MSG}
            return

        citations = build_citations(chunks)  # all reranked passages
        yield {
            "type": "citations",
            "citations": [c.model_dump(mode="json") for c in citations],
        }

        parts: list[str] = []
        async for delta in self.generator.stream(query, chunks, history):
            parts.append(delta)
            yield {"type": "token", "text": delta}

        yield {"type": "done", "answer": "".join(parts)}


def _history_to_text(history: list[LLMMessage] | None, max_turns: int = 6) -> str | None:
    if not history:
        return None
    recent = history[-max_turns:]
    return "\n".join(f"{m['role']}: {m['content']}" for m in recent)
