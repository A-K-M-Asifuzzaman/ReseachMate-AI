from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.agent import AgentRequest, AgentResponse
from app.services import chat_service
from app.services.agents import AgentOrchestrator
from app.services.agents.base import AgentContext

router = APIRouter(prefix="/agents", tags=["agents"])

_orchestrator: AgentOrchestrator | None = None


def _get_orchestrator() -> AgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


@router.post("/run", response_model=AgentResponse)
async def run_agent(
    payload: AgentRequest, current_user: CurrentUser, db: DbSession
) -> AgentResponse:
    history = []
    if payload.conversation_id:
        history = await chat_service.load_history(db, payload.conversation_id)

    ctx = AgentContext(
        db=db,
        user_id=current_user.id,
        document_ids=payload.document_ids,
        history=history,
    )
    return await _get_orchestrator().run(payload.query, ctx, forced=payload.agent)
