from __future__ import annotations

import json

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.core.deps import CurrentUser, DbSession
from app.core.metrics import metrics
from app.models.chat import MessageRole
from app.schemas.rag import Citation, RAGAnswer, RAGQueryRequest
from app.services import chat_service
from app.services.rag import RAGPipeline

router = APIRouter(prefix="/rag", tags=["rag"])

_pipeline: RAGPipeline | None = None


def get_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline


@router.post("/query", response_model=RAGAnswer)
async def query(
    payload: RAGQueryRequest, current_user: CurrentUser, db: DbSession
) -> RAGAnswer:
    convo = await chat_service.get_or_create_conversation(
        db,
        current_user.id,
        payload.conversation_id,
        document_ids=payload.document_ids,
        first_message=payload.query,
    )
    history = await chat_service.load_history(db, convo.id)

    answer = await get_pipeline().run(
        payload.query,
        db=db,
        user_id=current_user.id,
        document_ids=[str(d) for d in payload.document_ids] if payload.document_ids else None,
        history=history,
        top_k=payload.top_k,
        rerank_top_n=payload.rerank_top_n,
    )
    answer.conversation_id = convo.id

    metrics.record_query(
        latency_ms=answer.latency_ms or 0,
        tokens=answer.tokens_used or 0,
        grounded=bool(answer.citations),
    )

    await chat_service.add_message(db, convo.id, MessageRole.USER, payload.query)
    await chat_service.add_message(
        db, convo.id, MessageRole.ASSISTANT, answer.answer, answer.citations
    )
    return answer


@router.post("/query/stream")
async def query_stream(
    payload: RAGQueryRequest, current_user: CurrentUser, db: DbSession
) -> EventSourceResponse:
    convo = await chat_service.get_or_create_conversation(
        db,
        current_user.id,
        payload.conversation_id,
        document_ids=payload.document_ids,
        first_message=payload.query,
    )
    history = await chat_service.load_history(db, convo.id)

    async def event_generator():
        final_answer = ""
        citations: list[Citation] = []
        yield {"event": "meta", "data": json.dumps({"conversation_id": str(convo.id)})}

        async for event in get_pipeline().run_stream(
            payload.query,
            db=db,
            user_id=current_user.id,
            document_ids=[str(d) for d in payload.document_ids]
            if payload.document_ids
            else None,
            history=history,
            top_k=payload.top_k,
            rerank_top_n=payload.rerank_top_n,
        ):
            etype = event["type"]
            if etype == "citations":
                citations = [Citation(**c) for c in event["citations"]]
            elif etype == "done":
                final_answer = event["answer"]
            yield {"event": etype, "data": json.dumps(event)}

        # Persist the turn once streaming completes.
        await chat_service.add_message(db, convo.id, MessageRole.USER, payload.query)
        await chat_service.add_message(
            db, convo.id, MessageRole.ASSISTANT, final_answer, citations
        )
        yield {"event": "saved", "data": "{}"}

    return EventSourceResponse(event_generator())
