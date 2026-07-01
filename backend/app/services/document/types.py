from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractedPage:
    page_number: int  # 1-based
    text: str
    tables: list[list[list[str]]] = field(default_factory=list)


@dataclass
class ExtractedDocument:
    pages: list[ExtractedPage]
    metadata: dict[str, Any] = field(default_factory=dict)
    references: list[str] = field(default_factory=list)

    @property
    def num_pages(self) -> int:
        return len(self.pages)

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages)


@dataclass
class TextChunk:
    """A ready-to-embed chunk with citation locators."""

    index: int
    content: str
    page_number: int | None = None
    section: str | None = None
    token_count: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
