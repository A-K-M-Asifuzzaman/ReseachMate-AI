from __future__ import annotations

from typing import AsyncIterator

from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.services.llm.base import BaseLLM, LLMMessage, LLMResponse

_MAX_TOKENS_DEFAULT = 2048


def _split_system(messages: list[LLMMessage]) -> tuple[str | None, list[dict]]:
    """Anthropic takes the system prompt separately from the message list."""
    system: str | None = None
    convo: list[dict] = []
    for m in messages:
        if m["role"] == "system":
            system = (system + "\n\n" + m["content"]) if system else m["content"]
        else:
            convo.append({"role": m["role"], "content": m["content"]})
    return system, convo


class AnthropicLLM(BaseLLM):
    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        from anthropic import AsyncAnthropic

        key = api_key or settings.ANTHROPIC_API_KEY
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set.")
        self.default_model = model or settings.LLM_MODEL
        self._client = AsyncAnthropic(api_key=key)

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
        system, convo = _split_system(messages)
        resp = await self._client.messages.create(
            model=model or self.default_model,
            system=system or "",
            messages=convo,
            temperature=settings.LLM_TEMPERATURE if temperature is None else temperature,
            max_tokens=max_tokens or _MAX_TOKENS_DEFAULT,
        )
        text = "".join(block.text for block in resp.content if block.type == "text")
        return LLMResponse(
            content=text,
            model=resp.model,
            prompt_tokens=resp.usage.input_tokens,
            completion_tokens=resp.usage.output_tokens,
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        system, convo = _split_system(messages)
        async with self._client.messages.stream(
            model=model or self.default_model,
            system=system or "",
            messages=convo,
            temperature=settings.LLM_TEMPERATURE if temperature is None else temperature,
            max_tokens=max_tokens or _MAX_TOKENS_DEFAULT,
        ) as stream:
            async for text in stream.text_stream:
                yield text
