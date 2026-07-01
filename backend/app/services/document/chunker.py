from __future__ import annotations

import re

from app.core.config import settings
from app.services.document.types import ExtractedDocument, TextChunk

# Common scientific section headings (with optional leading numbering like "3.1").
_SECTION_NAMES = (
    r"abstract|introduction|related work|background|preliminaries|methodology|methods?|"
    r"approach|materials and methods|experimental setup|experiments?|dataset|data|model|"
    r"architecture|results?|evaluation|analysis|discussion|ablation|limitations?|"
    r"conclusions?|future work|acknowledg(e)?ments?|references|appendix"
)
_SECTION_HEADING = re.compile(
    rf"^\s*(?:\d+(?:\.\d+)*\.?\s+)?({_SECTION_NAMES})\b.{{0,60}}$",
    re.IGNORECASE,
)
_NUMBERED_HEADING = re.compile(r"^\s*\d+(?:\.\d+){0,2}\.?\s+[A-Z][A-Za-z].{0,70}$")

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 90:
        return False
    return bool(_SECTION_HEADING.match(stripped) or _NUMBERED_HEADING.match(stripped))


def _approx_tokens(text: str) -> int:
    # ~4 chars/token is a good rule of thumb for English scientific text.
    return max(1, len(text) // 4)


def _split_large(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Recursively split an over-long block on paragraph → sentence → word boundaries."""
    if len(text) <= chunk_size:
        return [text]

    # First try to split on sentences; fall back to hard word windows.
    units = _SENTENCE_SPLIT.split(text)
    if len(units) == 1:
        units = text.split(" ")

    chunks: list[str] = []
    current = ""
    for unit in units:
        candidate = f"{current} {unit}".strip()
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(current)
        # Start next chunk with a character overlap tail for context continuity.
        tail = current[-overlap:] if overlap and current else ""
        current = f"{tail} {unit}".strip()
    if current:
        chunks.append(current)
    return chunks


def _build_blocks(doc: ExtractedDocument) -> list[tuple[str, int, str]]:
    """Return (paragraph_text, page_number, section) triples in reading order."""
    blocks: list[tuple[str, int, str]] = []
    current_section = "Body"

    for page in doc.pages:
        # Split page text into paragraphs on blank lines.
        for para in re.split(r"\n\s*\n", page.text):
            lines = para.splitlines()
            if not lines:
                continue

            # A one-line paragraph that is a heading updates the section pointer.
            if len(lines) == 1 and _is_heading(lines[0]):
                current_section = lines[0].strip().title()
                continue

            # A heading may also lead a paragraph; capture it and keep the body.
            if _is_heading(lines[0]):
                current_section = lines[0].strip().title()
                body = "\n".join(lines[1:]).strip()
            else:
                body = para.strip()

            if body:
                blocks.append((body, page.page_number, current_section))
    return blocks


def chunk_document(
    doc: ExtractedDocument,
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[TextChunk]:
    """Semantic-ish chunking: pack section-aware paragraph blocks into ~chunk_size
    windows without splitting mid-paragraph unless a paragraph is itself too large.
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP

    blocks = _build_blocks(doc)
    chunks: list[TextChunk] = []
    idx = 0

    buffer = ""
    buf_page: int | None = None
    buf_section: str | None = None

    def flush() -> None:
        nonlocal buffer, buf_page, buf_section, idx
        text = buffer.strip()
        if text:
            chunks.append(
                TextChunk(
                    index=idx,
                    content=text,
                    page_number=buf_page,
                    section=buf_section,
                    token_count=_approx_tokens(text),
                )
            )
            idx += 1
        buffer = ""
        buf_page = None
        buf_section = None

    for body, page, section in blocks:
        # A section change is a natural chunk boundary.
        if buffer and section != buf_section:
            flush()

        for piece in _split_large(body, chunk_size, overlap):
            if buf_page is None:
                buf_page, buf_section = page, section
            if len(buffer) + len(piece) + 1 <= chunk_size:
                buffer = f"{buffer}\n{piece}".strip()
            else:
                flush()
                buf_page, buf_section = page, section
                buffer = piece

    flush()
    return chunks
