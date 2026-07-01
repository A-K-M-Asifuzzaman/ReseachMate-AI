from __future__ import annotations

from abc import ABC, abstractmethod


class BaseEmbedder(ABC):
    """Provider-agnostic embedding interface.

    Retrieval models (BGE/E5) often need *different* handling for the query vs. the
    passages being indexed, so the two are separate methods.
    """

    dimension: int

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed passages for indexing."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a single search query."""

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(t) for t in texts]
