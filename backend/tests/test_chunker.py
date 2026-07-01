from app.services.document.chunker import chunk_document
from app.services.document.cleaner import clean_document
from app.services.document.types import ExtractedDocument, ExtractedPage


def _make_doc() -> ExtractedDocument:
    page1 = ExtractedPage(
        page_number=1,
        text=(
            "Introduction\n"
            "This paper studies attention mechanisms. " * 20
            + "\n\nMethodology\n"
            + "We propose a transformer architecture. " * 20
        ),
    )
    page2 = ExtractedPage(
        page_number=2,
        text="Results\n" + "Our model outperforms the baseline. " * 30,
    )
    return ExtractedDocument(pages=[page1, page2])


def test_chunks_are_bounded_and_sectioned():
    chunks = chunk_document(_make_doc(), chunk_size=500, overlap=50)
    assert chunks, "expected at least one chunk"

    # Chunk sizes stay near the target (allow slack for boundary merges).
    assert all(len(c.content) <= 900 for c in chunks)

    # Section labels are detected from headings.
    sections = {c.section for c in chunks}
    assert any("Introduction" in (s or "") for s in sections)
    assert any("Methodology" in (s or "") for s in sections)
    assert any("Results" in (s or "") for s in sections)

    # Indices are contiguous and page numbers are attached.
    assert [c.index for c in chunks] == list(range(len(chunks)))
    assert all(c.page_number in (1, 2) for c in chunks)


def test_cleaner_removes_repeated_headers_and_hyphenation():
    pages = [
        ExtractedPage(page_number=i, text="ACME JOURNAL\nInter-\nesting content here.\n1")
        for i in range(1, 6)
    ]
    doc = ExtractedDocument(pages=pages)
    cleaned = clean_document(doc)
    joined = cleaned.full_text
    assert "Interesting content here." in joined  # de-hyphenated
    assert "ACME JOURNAL" not in joined  # repeated header stripped
