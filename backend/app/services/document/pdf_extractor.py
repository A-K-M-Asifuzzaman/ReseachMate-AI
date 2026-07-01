from __future__ import annotations

import re

from app.core.logging import get_logger
from app.services.document.types import ExtractedDocument, ExtractedPage

logger = get_logger(__name__)

_REFERENCES_HEADING = re.compile(r"^\s*(references|bibliography)\s*$", re.IGNORECASE)


def _extract_tables(pdf_path: str) -> dict[int, list[list[list[str]]]]:
    """Best-effort table extraction with pdfplumber, keyed by 1-based page number.

    pdfplumber is slower and can fail on some PDFs, so failures are swallowed — tables
    are a nice-to-have, not required for the RAG core.
    """
    tables_by_page: dict[int, list] = {}
    try:
        import pdfplumber

        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                try:
                    tables = page.extract_tables()
                except Exception:  # noqa: BLE001
                    tables = []
                if tables:
                    tables_by_page[i] = tables
    except Exception as exc:  # noqa: BLE001
        logger.warning("table_extraction_failed", error=str(exc))
    return tables_by_page


def extract_pdf(pdf_path: str, *, with_tables: bool = True) -> ExtractedDocument:
    """Extract per-page text + document metadata using PyMuPDF (fast, reliable)."""
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    meta = doc.metadata or {}

    tables_by_page = _extract_tables(pdf_path) if with_tables else {}

    pages: list[ExtractedPage] = []
    references: list[str] = []
    in_references = False

    for i, page in enumerate(doc, start=1):
        text = page.get_text("text")
        pages.append(
            ExtractedPage(
                page_number=i,
                text=text,
                tables=tables_by_page.get(i, []),
            )
        )
        # Collect reference lines once we hit a References heading.
        for line in text.splitlines():
            if _REFERENCES_HEADING.match(line):
                in_references = True
                continue
            if in_references and line.strip():
                references.append(line.strip())

    extracted = ExtractedDocument(
        pages=pages,
        metadata={
            "pdf_title": (meta.get("title") or "").strip(),
            "pdf_author": (meta.get("author") or "").strip(),
            "pdf_subject": (meta.get("subject") or "").strip(),
            "pdf_keywords": (meta.get("keywords") or "").strip(),
            "creation_date": (meta.get("creationDate") or "").strip(),
        },
        references=references[:200],  # cap to avoid bloat
    )
    doc.close()
    logger.info("pdf_extracted", pages=extracted.num_pages, path=pdf_path)
    return extracted
