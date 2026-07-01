from __future__ import annotations

from functools import lru_cache

from app.services.vectorstore.base import BaseVectorStore


@lru_cache
def get_vector_store() -> BaseVectorStore:
    from app.services.vectorstore.qdrant_store import QdrantVectorStore

    return QdrantVectorStore()
