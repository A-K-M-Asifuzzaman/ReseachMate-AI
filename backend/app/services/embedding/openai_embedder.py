from __future__ import annotations

from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger
from app.services.embedding.base import BaseEmbedder

logger = get_logger(__name__)

_BATCH = 128  # OpenAI accepts many inputs per call; batch to cut round-trips


class OpenAIEmbedder(BaseEmbedder):
    """Embeddings via the OpenAI API (e.g. text-embedding-3-small).

    Chosen for cheap, dependency-light deployment: no torch, no model download, tiny
    memory footprint — so the backend fits any free hosting tier. text-embedding-3-*
    models support the ``dimensions`` parameter, so the vector size always matches the
    configured ``EMBEDDING_DIM`` (and thus the Qdrant collection).
    """

    def __init__(
        self,
        model: str | None = None,
        dimension: int | None = None,
        api_key: str | None = None,
    ) -> None:
        from openai import OpenAI

        key = api_key or settings.OPENAI_API_KEY
        if not key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI embeddings.")
        self.model = model or settings.EMBEDDING_MODEL
        self.dimension = dimension or settings.EMBEDDING_DIM
        self._supports_dim = self.model.startswith("text-embedding-3")
        self._client = OpenAI(api_key=key)
        logger.info("openai_embedder_ready", model=self.model, dim=self.dimension)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _embed(self, texts: list[str]) -> list[list[float]]:
        kwargs: dict = {"model": self.model, "input": texts}
        if self._supports_dim:
            kwargs["dimensions"] = self.dimension
        resp = self._client.embeddings.create(**kwargs)
        return [d.embedding for d in resp.data]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        out: list[list[float]] = []
        for i in range(0, len(texts), _BATCH):
            out.extend(self._embed(texts[i : i + _BATCH]))
        return out

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]
