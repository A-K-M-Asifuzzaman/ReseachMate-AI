"""Application settings, loaded from environment / .env.

All configuration lives here so the rest of the app depends on a single typed
`settings` object rather than reading `os.environ` in scattered places.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from urllib.parse import quote_plus

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── App ────────────────────────────────────────────────────────────────
    APP_NAME: str = "ResearchMate AI"
    ENVIRONMENT: Literal["development", "production", "test"] = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    # Comma-separated string to sidestep pydantic-settings JSON-decoding list envs.
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]

    # ─── Security / JWT ─────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─── PostgreSQL ─────────────────────────────────────────────────────────
    POSTGRES_USER: str = "researchmate"
    POSTGRES_PASSWORD: str = "researchmate"
    POSTGRES_DB: str = "researchmate"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str | None = None
    SQL_ECHO: bool = False  # log every SQL statement (very verbose)
    # Create tables at startup even in production (skip Alembic). Handy for a
    # one-click free-tier deploy; prefer migrations for real production.
    AUTO_CREATE_TABLES: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        user = quote_plus(self.POSTGRES_USER)
        password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql+asyncpg://{user}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ─── Qdrant ─────────────────────────────────────────────────────────────
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str | None = None
    QDRANT_COLLECTION: str = "researchmate_chunks"

    # ─── Neo4j ──────────────────────────────────────────────────────────────
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "researchmate"

    # ─── LLM ────────────────────────────────────────────────────────────────
    LLM_PROVIDER: Literal["openai", "anthropic", "ollama"] = "openai"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_MODEL_HEAVY: str = "gpt-4o"
    LLM_TEMPERATURE: float = 0.1
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # ─── Embeddings ─────────────────────────────────────────────────────────
    EMBEDDING_PROVIDER: str = "sentence_transformers"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIM: int = 384
    EMBEDDING_DEVICE: str = "cpu"

    # ─── Reranker ───────────────────────────────────────────────────────────
    RERANKER_ENABLED: bool = True
    RERANKER_MODEL: str = "BAAI/bge-reranker-base"

    # ─── Retrieval tuning ───────────────────────────────────────────────────
    RETRIEVAL_TOP_K: int = 20
    RERANK_TOP_N: int = 6
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150
    # pdfplumber table extraction is CPU-heavy (pure-Python, holds the GIL) and the
    # tables aren't used by retrieval — keep it off, especially on small instances.
    EXTRACT_TABLES: bool = False

    # ─── Storage ────────────────────────────────────────────────────────────
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    STORAGE_DIR: str = "./storage"
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    S3_BUCKET: str | None = None
    S3_REGION: str | None = None

    # ─── Limits ─────────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60
    MAX_UPLOAD_MB: int = 50

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton (import this everywhere)."""
    return Settings()


settings = get_settings()
