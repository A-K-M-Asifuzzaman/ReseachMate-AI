from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Conversation, Message, MessageRole
from app.schemas.rag import Citation
from app.services.llm.base import LLMMessage

_HISTORY_LIMIT = 10  # last N messages fed back to the LLM as memory


async def get_conversation(
    db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID
) -> Conversation:
    convo = await db.get(Conversation, conversation_id)
    if convo is None or convo.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found."
        )
    return convo


async def create_conversation(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    title: str | None = None,
    document_ids: list[uuid.UUID] | None = None,
) -> Conversation:
    convo = Conversation(
        user_id=user_id,
        title=title or "New conversation",
        document_ids=[str(d) for d in (document_ids or [])],
    )
    db.add(convo)
    await db.commit()
    await db.refresh(convo)
    return convo


async def get_or_create_conversation(
    db: AsyncSession,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID | None,
    *,
    document_ids: list[uuid.UUID] | None = None,
    first_message: str | None = None,
) -> Conversation:
    if conversation_id:
        return await get_conversation(db, conversation_id, user_id)
    title = (first_message[:60] + "…") if first_message and len(first_message) > 60 else first_message
    return await create_conversation(
        db, user_id, title=title, document_ids=document_ids
    )


async def load_history(db: AsyncSession, conversation_id: uuid.UUID) -> list[LLMMessage]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(_HISTORY_LIMIT)
    )
    rows = (await db.execute(stmt)).scalars().all()
    rows.reverse()  # chronological order for the LLM
    return [{"role": m.role.value, "content": m.content} for m in rows]  # type: ignore[misc]


async def add_message(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    role: MessageRole,
    content: str,
    citations: list[Citation] | None = None,
) -> Message:
    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        citations=[c.model_dump(mode="json") for c in (citations or [])],
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def list_conversations(
    db: AsyncSession, user_id: uuid.UUID
) -> tuple[list[Conversation], int]:
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    items = list((await db.execute(stmt)).scalars().all())
    total = (
        await db.execute(
            select(func.count()).select_from(Conversation).where(
                Conversation.user_id == user_id
            )
        )
    ).scalar_one()
    return items, total
