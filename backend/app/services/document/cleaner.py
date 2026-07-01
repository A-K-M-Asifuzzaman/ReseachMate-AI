from __future__ import annotations

import re
from collections import Counter

from app.services.document.types import ExtractedDocument, ExtractedPage

# NUL (0x00) and other C0 control chars. Postgres text/jsonb cannot store NUL, and
# PDFs not-infrequently yield them; strip them (keep tab/newline/carriage-return).
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# Hyphenation at line breaks:  "atten-\ntion"  ->  "attention"
_HYPHEN_BREAK = re.compile(r"(\w+)-\n(\w+)")


def sanitize_text(text: str) -> str:
    """Remove characters Postgres can't store (NUL + control chars)."""
    if not text:
        return text
    return _CONTROL_CHARS.sub("", text)
# Collapse 3+ newlines and stray whitespace
_MULTI_NEWLINE = re.compile(r"\n{3,}")
_TRAILING_WS = re.compile(r"[ \t]+\n")
# Page-number-only lines and common footer noise
_PAGE_NUMBER_LINE = re.compile(r"^\s*\d{1,4}\s*$")
_URL_FOOTER = re.compile(r"^\s*(https?://\S+|www\.\S+|doi:\S+)\s*$", re.IGNORECASE)


def _detect_repeated_lines(pages: list[ExtractedPage], threshold: float = 0.5) -> set[str]:
    """Lines that appear on many pages are almost always headers/footers."""
    if len(pages) < 3:
        return set()
    counter: Counter[str] = Counter()
    for page in pages:
        seen_on_page = set()
        for line in page.text.splitlines():
            norm = line.strip()
            if 0 < len(norm) < 120:
                seen_on_page.add(norm)
        counter.update(seen_on_page)

    cutoff = max(2, int(len(pages) * threshold))
    return {line for line, count in counter.items() if count >= cutoff}


def _clean_line(line: str) -> str | None:
    stripped = line.strip()
    if not stripped:
        return ""
    if _PAGE_NUMBER_LINE.match(stripped):
        return None
    if _URL_FOOTER.match(stripped):
        return None
    return line


def clean_document(doc: ExtractedDocument) -> ExtractedDocument:
    """Remove headers/footers/page-numbers and normalise whitespace, in place-ish."""
    repeated = _detect_repeated_lines(doc.pages)

    cleaned_pages: list[ExtractedPage] = []
    for page in doc.pages:
        text = _HYPHEN_BREAK.sub(r"\1\2", sanitize_text(page.text))

        kept: list[str] = []
        for line in text.splitlines():
            if line.strip() in repeated:
                continue
            cl = _clean_line(line)
            if cl is None:
                continue
            kept.append(cl)

        text = "\n".join(kept)
        text = _TRAILING_WS.sub("\n", text)
        text = _MULTI_NEWLINE.sub("\n\n", text).strip()

        cleaned_pages.append(
            ExtractedPage(page_number=page.page_number, text=text, tables=page.tables)
        )

    doc.pages = cleaned_pages
    return doc
