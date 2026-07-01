from __future__ import annotations

import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.deps import CurrentUser, DbSession
from app.core.logging import get_logger
from app.models.chunk import Chunk
from app.models.document import Document, DocumentStatus
from app.schemas.document import (
    ChunkPublic,
    DocumentListResponse,
    DocumentPublic,
    DocumentUpdate,
)
from app.services.document import DocumentPipeline
from app.services.storage import get_storage
from app.services.vectorstore import get_vector_store

router = APIRouter(prefix="/documents", tags=["documents"])
logger = get_logger(__name__)

_PDF_MAGIC = b"%PDF-"


async def _ingest_in_background(document_id: uuid.UUID) -> None:
    """Runs after the response is sent; uses its own DB session."""
    async with AsyncSessionLocal() as db:
        document = await db.get(Document, document_id)
        if document is None:
            return
        try:
            await DocumentPipeline().ingest(document=document, db=db)
        except Exception as exc:  # noqa: BLE001  (already recorded on the document)
            logger.error("background_ingest_error", doc=str(document_id), error=str(exc))


@router.post("/upload", response_model=DocumentPublic, status_code=status.HTTP_201_CREATED)
async def upload_document(
    current_user: CurrentUser,
    db: DbSession,
    background: BackgroundTasks,
    file: UploadFile = File(...),
) -> DocumentPublic:
    if (file.content_type or "") not in ("application/pdf", "application/x-pdf"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only PDF files are supported.",
        )

    data = await file.read()
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.MAX_UPLOAD_MB} MB limit.",
        )
    if not data.startswith(_PDF_MAGIC):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File does not look like a valid PDF.",
        )

    storage = get_storage()
    path = await storage.save(
        data, filename=file.filename or "document.pdf", user_id=str(current_user.id)
    )

    document = Document(
        user_id=current_user.id,
        title=file.filename or "Untitled",
        filename=file.filename or "document.pdf",
        storage_path=path,
        file_size=len(data),
        status=DocumentStatus.UPLOADED,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    background.add_task(_ingest_in_background, document.id)
    return DocumentPublic.model_validate(document)


@router.get("", response_model=DocumentListResponse)
async def list_documents(current_user: CurrentUser, db: DbSession) -> DocumentListResponse:
    stmt = (
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
    )
    items = list((await db.execute(stmt)).scalars().all())
    total = (
        await db.execute(
            select(func.count()).select_from(Document).where(
                Document.user_id == current_user.id
            )
        )
    ).scalar_one()
    return DocumentListResponse(
        items=[DocumentPublic.model_validate(d) for d in items], total=total
    )


async def _get_owned_document(
    db: DbSession, document_id: uuid.UUID, user_id: uuid.UUID
) -> Document:
    document = await db.get(Document, document_id)
    if document is None or document.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found."
        )
    return document


@router.get("/{document_id}", response_model=DocumentPublic)
async def get_document(
    document_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> DocumentPublic:
    document = await _get_owned_document(db, document_id, current_user.id)
    return DocumentPublic.model_validate(document)


@router.get("/{document_id}/chunks", response_model=list[ChunkPublic])
async def list_chunks(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[ChunkPublic]:
    await _get_owned_document(db, document_id, current_user.id)
    stmt = (
        select(Chunk)
        .where(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index)
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [ChunkPublic.model_validate(c) for c in rows]


@router.patch("/{document_id}", response_model=DocumentPublic)
async def update_document(
    document_id: uuid.UUID,
    payload: DocumentUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> DocumentPublic:
    document = await _get_owned_document(db, document_id, current_user.id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(document, field, value)
    await db.commit()
    await db.refresh(document)
    return DocumentPublic.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID, current_user: CurrentUser, db: DbSession
):
    document = await _get_owned_document(db, document_id, current_user.id)

    # Remove vectors + stored file, then the row (chunks cascade in Postgres).
    await get_vector_store().delete_by_document(str(document_id))
    try:
        await get_storage().delete(document.storage_path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("file_delete_failed", error=str(exc))

    await db.delete(document)
    await db.commit()
