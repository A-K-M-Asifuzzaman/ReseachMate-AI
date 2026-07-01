from __future__ import annotations

from typing import AsyncIterator

from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger
from app.services.llm.base import BaseLLM, LLMMessage, LLMResponse

logger = get_logger(__name__)


class OpenAILLM(BaseLLM):
    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        from openai import AsyncOpenAI

        key = api_key or settings.OPENAI_API_KEY
        if not key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to your .env to use the OpenAI LLM."
            )
        self.default_model = model or settings.LLM_MODEL
        self._client = AsyncOpenAI(api_key=key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> LLMResponse:
        kwargs: dict = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": settings.LLM_TEMPERATURE
            if temperature is None
            else temperature,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        if response_format:
            kwargs["response_format"] = response_format

        resp = await self._client.chat.completions.create(**kwargs)
        usage = resp.usage
        return LLMResponse(
            content=resp.choices[0].message.content or "",
            model=resp.model,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        kwargs: dict = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": settings.LLM_TEMPERATURE
            if temperature is None
            else temperature,
            "stream": True,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        stream = await self._client.chat.completions.create(**kwargs)
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
