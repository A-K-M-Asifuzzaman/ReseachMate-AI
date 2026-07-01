from __future__ import annotations

import threading

from app.core.config import settings
from app.core.logging import get_logger
from app.services.embedding.base import BaseEmbedder

logger = get_logger(__name__)

# Retrieval instruction prefixes. BGE/E5 models are trained to embed queries with a
# short instruction; passages are embedded as-is (BGE) or with a "passage:" prefix (E5).
_QUERY_PREFIXES = {
    "bge": "Represent this sentence for searching relevant passages: ",
    "e5": "query: ",
    "generic": "",
}
_DOC_PREFIXES = {
    "bge": "",
    "e5": "passage: ",
    "generic": "",
}


def _family(model_name: str) -> str:
    name = model_name.lower()
    if "e5" in name:
        return "e5"
    if "bge" in name:
        return "bge"
    return "generic"  # e.g. all-MiniLM — trained without an instruction prefix


class SentenceTransformerEmbedder(BaseEmbedder):
    """Local embeddings via sentence-transformers (BGE / E5 / any ST model).

    The heavy model is loaded lazily on first use so importing this module (and thus
    starting the API) stays fast and doesn't require the weights to be present.
    """

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        dimension: int | None = None,
    ) -> None:
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.device = device or settings.EMBEDDING_DEVICE
        self.dimension = dimension or settings.EMBEDDING_DIM
        self._family = _family(self.model_name)
        self._model = None
        self._lock = threading.Lock()

    def _ensure_model(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from sentence_transformers import SentenceTransformer

                    logger.info(
                        "loading_embedding_model",
                        model=self.model_name,
                        device=self.device,
                    )
                    self._model = SentenceTransformer(
                        self.model_name, device=self.device
                    )
                    actual = self._model.get_sentence_embedding_dimension()
                    if actual != self.dimension:
                        logger.warning(
                            "embedding_dim_mismatch",
                            configured=self.dimension,
                            actual=actual,
                        )
                        self.dimension = actual
        return self._model

    def _encode(self, texts: list[str]) -> list[list[float]]:
        model = self._ensure_model()
        vectors = model.encode(
            texts,
            batch_size=32,
            normalize_embeddings=True,  # cosine similarity via dot product
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return vectors.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        prefix = _DOC_PREFIXES[self._family]
        prepared = [prefix + t for t in texts] if prefix else texts
        return self._encode(prepared)

    def embed_query(self, text: str) -> list[float]:
        prefix = _QUERY_PREFIXES[self._family]
        return self._encode([prefix + text])[0]
