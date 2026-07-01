from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app import __version__
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import init_db
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
    enabled=settings.is_production,  # avoid throttling local dev
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("startup", app=settings.APP_NAME, env=settings.ENVIRONMENT)

    # Create tables in dev (or when AUTO_CREATE_TABLES is set); production should
    # normally run Alembic migrations instead.
    if settings.ENVIRONMENT != "production" or settings.AUTO_CREATE_TABLES:
        try:
            await init_db()
        except Exception as exc:  # noqa: BLE001
            logger.error("init_db_failed", error=str(exc))

    # Pre-create the Qdrant collection so first upload doesn't race.
    try:
        from app.services.vectorstore import get_vector_store

        await get_vector_store().ensure_collection()
    except Exception as exc:  # noqa: BLE001
        logger.warning("qdrant_unavailable_at_startup", error=str(exc))

    # Warm the embedding model now (loads/downloads weights once) so no incoming
    # HTTP request — e.g. registration during an upload — is ever starved by a
    # first-time model load happening on a worker thread.
    import asyncio

    try:
        from app.services.embedding import get_embedder

        embedder = get_embedder()
        await asyncio.to_thread(embedder.embed_query, "warmup")
        logger.info("embedding_model_warmed", model=settings.EMBEDDING_MODEL)
    except Exception as exc:  # noqa: BLE001
        logger.warning("embedding_warmup_failed", error=str(exc))

    yield

    # Shutdown: close the Neo4j driver if it was opened.
    try:
        from app.services.knowledge_graph.neo4j_store import get_neo4j_store

        await get_neo4j_store().close()
    except Exception:  # noqa: BLE001
        pass
    logger.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=__version__,
        description="RAG research assistant — upload papers, ask cited questions, "
        "summarize, compare, and explore a knowledge graph.",
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_timing(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time-ms"] = f"{elapsed_ms:.1f}"
        if request.url.path.startswith(settings.API_V1_PREFIX):
            logger.info(
                "request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                latency_ms=round(elapsed_ms, 1),
            )
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error("unhandled_error", path=request.url.path, error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error."},
        )

    @app.get("/health", tags=["system"])
    async def health() -> dict:
        return {"status": "ok", "version": __version__, "env": settings.ENVIRONMENT}

    @app.get("/", tags=["system"])
    async def root() -> dict:
        return {"name": settings.APP_NAME, "docs": "/docs"}

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    return app


app = create_app()
