from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VectorRecord:
    """A vector point to index. ``id`` mirrors the Postgres chunk id."""

    id: str
    vector: list[float]
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorSearchHit:
    id: str
    score: float
    payload: dict[str, Any] = field(default_factory=dict)


class BaseVectorStore(ABC):
    @abstractmethod
    async def ensure_collection(self) -> None: ...

    @abstractmethod
    async def upsert(self, records: list[VectorRecord]) -> None: ...

    @abstractmethod
    async def search(
        self,
        query_vector: list[float],
        *,
        top_k: int = 20,
        user_id: str | None = None,
        document_ids: list[str] | None = None,
    ) -> list[VectorSearchHit]: ...

    @abstractmethod
    async def delete_by_document(self, document_id: str) -> None: ...
