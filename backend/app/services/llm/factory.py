from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.services.llm.base import BaseLLM


@lru_cache
def get_llm(model: str | None = None) -> BaseLLM:
    """Return an LLM client for the configured provider.

    Pass ``model`` to pin a specific model (e.g. the heavier model for KG extraction);
    results are cached per (provider, model).
    """
    provider = settings.LLM_PROVIDER.lower()

    if provider == "openai":
        from app.services.llm.openai_llm import OpenAILLM

        return OpenAILLM(model=model)

    if provider == "anthropic":
        from app.services.llm.anthropic_llm import AnthropicLLM

        return AnthropicLLM(model=model)

    if provider == "ollama":
        # Ollama exposes an OpenAI-compatible API; reuse the OpenAI client.
        from openai import AsyncOpenAI

        from app.services.llm.openai_llm import OpenAILLM

        llm = OpenAILLM.__new__(OpenAILLM)
        llm.default_model = model or settings.LLM_MODEL
        llm._client = AsyncOpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL}/v1", api_key="ollama"
        )
        return llm

    raise ValueError(f"Unknown LLM_PROVIDER: {settings.LLM_PROVIDER!r}")


def get_heavy_llm() -> BaseLLM:
    """LLM tuned for hard reasoning tasks (KG extraction, agent planning)."""
    return get_llm(model=settings.LLM_MODEL_HEAVY)
