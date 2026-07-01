from __future__ import annotations

import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.chunk import Chunk
from app.models.document import Document, DocumentStatus
from app.services.document.chunker import chunk_document
from app.services.document.cleaner import clean_document
from app.services.document.metadata import extract_bibliographic_metadata
from app.services.document.pdf_extractor import extract_pdf
from app.services.document.types import TextChunk
from app.services.embedding import get_embedder
from app.services.storage import get_storage
from app.services.vectorstore import VectorRecord, get_vector_store

logger = get_logger(__name__)


class DocumentPipeline:
    """Turn an uploaded PDF into cleaned, chunked, embedded, searchable content."""

    def __init__(self) -> None:
        self.storage = get_storage()
        self.embedder = get_embedder()
        self.vector_store = get_vector_store()

    def _extract_and_chunk(self, local_path: str) -> tuple[dict, list[TextChunk], int]:
        """Blocking CPU work — run inside a thread."""
        extracted = extract_pdf(local_path, with_tables=True)
        extracted = clean_document(extracted)
        bib = extract_bibliographic_metadata(extracted)
        chunks = chunk_document(extracted)
        return bib, chunks, extracted.num_pages

    def _embed(self, texts: list[str]) -> list[list[float]]:
        return self.embedder.embed_documents(texts)

    async def ingest(self, *, document: Document, db: AsyncSession) -> Document:
        document.status = DocumentStatus.PROCESSING
        await db.commit()

        try:
            local_path = self.storage.local_path(document.storage_path)

            bib, chunks, num_pages = await asyncio.to_thread(
                self._extract_and_chunk, local_path
            )
            if not chunks:
                raise ValueError("No extractable text found in PDF.")

            embeddings = await asyncio.to_thread(
                self._embed, [c.content for c in chunks]
            )

            await self.vector_store.ensure_collection()

            records: list[VectorRecord] = []
            for chunk, vector in zip(chunks, embeddings):
                chunk_id = uuid.uuid4()
                db.add(
                    Chunk(
                        id=chunk_id,
                        document_id=document.id,
                        user_id=document.user_id,
                        chunk_index=chunk.index,
                        content=chunk.content,
                        page_number=chunk.page_number,
                        section=chunk.section,
                        token_count=chunk.token_count,
                        chunk_metadata=chunk.metadata,
                    )
                )
                records.append(
                    VectorRecord(
                        id=str(chunk_id),
                        vector=vector,
                        payload={
                            "chunk_id": str(chunk_id),
                            "document_id": str(document.id),
                            "user_id": str(document.user_id),
                            "chunk_index": chunk.index,
                            "page_number": chunk.page_number,
                            "section": chunk.section,
                            "content": chunk.content,
                        },
                    )
                )

            await self.vector_store.upsert(records)

            # Fill in bibliographic fields only where the user hasn't provided them.
            if not document.title or document.title == document.filename:
                document.title = bib["title"] or document.filename
            document.authors = document.authors or bib["authors"]
            document.year = document.year or bib["year"]
            document.abstract = document.abstract or bib["abstract"]
            document.num_pages = num_pages
            document.num_chunks = len(chunks)
            document.status = DocumentStatus.READY
            document.error = None

            await db.commit()
            await db.refresh(document)
            logger.info(
                "document_ingested",
                document_id=str(document.id),
                chunks=len(chunks),
                pages=num_pages,
            )
            return document

        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            document.status = DocumentStatus.FAILED
            document.error = str(exc)[:1000]
            await db.commit()
            logger.error(
                "document_ingest_failed",
                document_id=str(document.id),
                error=str(exc),
            )
            raise
