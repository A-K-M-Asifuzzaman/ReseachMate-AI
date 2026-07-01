from __future__ import annotations

import threading

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.rag import RetrievedChunk

logger = get_logger(__name__)


class CrossEncoderReranker:
    """Re-scores (query, chunk) pairs with a cross-encoder for precision.

    Cross-encoders read the query and passage jointly, so they are far more accurate
    than the bi-encoder used for first-stage retrieval — at the cost of running once
    per candidate, which is why we only rerank the fused shortlist.
    """

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.RERANKER_MODEL
        self._model = None
        self._lock = threading.Lock()

    def _ensure_model(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from sentence_transformers import CrossEncoder

                    logger.info("loading_reranker", model=self.model_name)
                    self._model = CrossEncoder(
                        self.model_name, device=settings.EMBEDDING_DEVICE
                    )
        return self._model

    def rerank(
        self, query: str, chunks: list[RetrievedChunk], top_n: int | None = None
    ) -> list[RetrievedChunk]:
        top_n = top_n or settings.RERANK_TOP_N
        if not chunks:
            return []
        if not settings.RERANKER_ENABLED:
            return chunks[:top_n]

        model = self._ensure_model()
        pairs = [[query, c.content] for c in chunks]
        scores = model.predict(pairs, show_progress_bar=False)

        for chunk, score in zip(chunks, scores):
            chunk.rerank_score = float(score)

        chunks.sort(key=lambda c: c.rerank_score, reverse=True)
        return chunks[:top_n]


_reranker: CrossEncoderReranker | None = None


def get_reranker() -> CrossEncoderReranker:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoderReranker()
    return _reranker
