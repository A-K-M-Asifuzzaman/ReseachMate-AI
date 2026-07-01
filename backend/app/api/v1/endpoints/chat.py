from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.chat import (
    ConversationCreate,
    ConversationDetail,
    ConversationListResponse,
    ConversationPublic,
    MessagePublic,
)
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/conversations", response_model=ConversationPublic, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate, current_user: CurrentUser, db: DbSession
) -> ConversationPublic:
    convo = await chat_service.create_conversation(
        db,
        current_user.id,
        title=payload.title,
        document_ids=payload.document_ids,
    )
    return ConversationPublic.model_validate(convo)


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    current_user: CurrentUser, db: DbSession
) -> ConversationListResponse:
    items, total = await chat_service.list_conversations(db, current_user.id)
    return ConversationListResponse(
        items=[ConversationPublic.model_validate(c) for c in items], total=total
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> ConversationDetail:
    convo = await chat_service.get_conversation(db, conversation_id, current_user.id)
    return ConversationDetail(
        id=convo.id,
        title=convo.title,
        document_ids=convo.document_ids,
        created_at=convo.created_at,
        updated_at=convo.updated_at,
        messages=[MessagePublic.model_validate(m) for m in convo.messages],
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID, current_user: CurrentUser, db: DbSession
):
    convo = await chat_service.get_conversation(db, conversation_id, current_user.id)
    await db.delete(convo)
    await db.commit()
