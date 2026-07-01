from __future__ import annotations

import re

from app.services.document.types import ExtractedDocument

_YEAR = re.compile(r"\b(19|20)\d{2}\b")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_ABSTRACT_HEADING = re.compile(r"\babstract\b", re.IGNORECASE)
_INTRO_HEADING = re.compile(r"\b(1\.?\s*)?introduction\b", re.IGNORECASE)


def _guess_title(first_page: str, pdf_title: str) -> str:
    """Prefer a clean PDF metadata title; else the first substantial line."""
    if pdf_title and len(pdf_title) > 5 and "untitled" not in pdf_title.lower():
        return pdf_title.strip()

    for line in first_page.splitlines():
        candidate = line.strip()
        # A title line: reasonably long, not an email/affiliation, not all caps noise.
        if 15 <= len(candidate) <= 250 and not _EMAIL.search(candidate):
            return candidate
    return "Untitled document"


def _guess_authors(first_page: str, pdf_author: str) -> str | None:
    if pdf_author and len(pdf_author) > 2:
        return pdf_author.strip()[:1024]

    lines = [line.strip() for line in first_page.splitlines() if line.strip()]
    # Authors usually sit just above the first email / affiliation on page 1.
    for i, line in enumerate(lines[:15]):
        if _EMAIL.search(line) and i > 0:
            candidate = lines[i - 1]
            if "," in candidate or " and " in candidate.lower():
                return candidate[:1024]
    return None


def _guess_year(text: str, pdf_meta: dict) -> int | None:
    created = pdf_meta.get("creation_date", "")
    m = _YEAR.search(created)
    if m:
        return int(m.group())
    m = _YEAR.search(text[:2000])
    return int(m.group()) if m else None


def _extract_abstract(full_text: str) -> str | None:
    m = _ABSTRACT_HEADING.search(full_text)
    if not m:
        return None
    start = m.end()
    end_match = _INTRO_HEADING.search(full_text, start)
    end = end_match.start() if end_match else start + 2000
    abstract = full_text[start:end].strip(" :\n\t")
    return abstract[:4000] if len(abstract) > 40 else None


def extract_bibliographic_metadata(doc: ExtractedDocument) -> dict:
    first_page = doc.pages[0].text if doc.pages else ""
    pdf_meta = doc.metadata

    title = _guess_title(first_page, pdf_meta.get("pdf_title", ""))
    authors = _guess_authors(first_page, pdf_meta.get("pdf_author", ""))
    year = _guess_year(doc.full_text, pdf_meta)
    abstract = _extract_abstract(doc.full_text)

    return {
        "title": title,
        "authors": authors,
        "year": year,
        "abstract": abstract,
    }
