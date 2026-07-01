from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    agents,
    auth,
    chat,
    comparison,
    documents,
    knowledge_graph,
    rag,
    summaries,
    system,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(rag.router)
api_router.include_router(chat.router)
api_router.include_router(summaries.router)
api_router.include_router(comparison.router)
api_router.include_router(knowledge_graph.router)
api_router.include_router(agents.router)
api_router.include_router(system.router)
