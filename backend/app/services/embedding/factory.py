from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.services.embedding.base import BaseEmbedder


@lru_cache
def get_embedder() -> BaseEmbedder:
    """Return the process-wide embedder singleton (model loaded once)."""
    provider = settings.EMBEDDING_PROVIDER.lower()

    if provider in ("sentence_transformers", "bge", "e5", "st"):
        from app.services.embedding.sentence_transformer import (
            SentenceTransformerEmbedder,
        )

        return SentenceTransformerEmbedder()

    if provider == "openai":
        from app.services.embedding.openai_embedder import OpenAIEmbedder

        return OpenAIEmbedder()

    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {settings.EMBEDDING_PROVIDER!r}")
