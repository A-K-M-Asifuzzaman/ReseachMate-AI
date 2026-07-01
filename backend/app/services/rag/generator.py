from __future__ import annotations

import re
from typing import AsyncIterator

from app.schemas.rag import Citation, RetrievedChunk
from app.services.llm import get_llm
from app.services.llm.base import LLMMessage

_SYSTEM = (
    "You are ResearchMate, a precise scientific research assistant. Answer the user's "
    "question using ONLY the numbered context passages provided. Rules:\n"
    "1. Ground every claim in the context and cite sources inline using bracketed "
    "numbers that match the passages, e.g. [1] or [2][3].\n"
    "2. If the context does not contain the answer, say so plainly — never invent "
    "facts, citations, or numbers.\n"
    "3. Be concise and technical. Prefer the paper's own terminology.\n"
    "4. When explaining methodology or results, reference the specific passage."
)

_CITE_REF = re.compile(r"\[(\d+)\]")
_SNIPPET_LEN = 300


def _format_context(chunks: list[RetrievedChunk]) -> str:
    blocks = []
    for i, c in enumerate(chunks, start=1):
        loc = []
        if c.page_number is not None:
            loc.append(f"p.{c.page_number}")
        if c.section:
            loc.append(c.section)
        locator = f" — {', '.join(loc)}" if loc else ""
        blocks.append(f"[{i}] ({c.title}{locator})\n{c.content}")
    return "\n\n".join(blocks)


def build_messages(
    query: str,
    chunks: list[RetrievedChunk],
    history: list[LLMMessage] | None = None,
) -> list[LLMMessage]:
    context = _format_context(chunks)
    messages: list[LLMMessage] = [{"role": "system", "content": _SYSTEM}]
    if history:
        messages.extend(history)
    messages.append(
        {
            "role": "user",
            "content": f"Context passages:\n\n{context}\n\nQuestion: {query}",
        }
    )
    return messages


def build_citations(
    chunks: list[RetrievedChunk], answer: str | None = None
) -> list[Citation]:
    """Build citation objects. If ``answer`` is given, keep only referenced passages;
    otherwise return all supplied chunks (used for streaming where we cite upfront)."""
    referenced: set[int] | None = None
    if answer is not None:
        referenced = {int(n) for n in _CITE_REF.findall(answer)}

    citations: list[Citation] = []
    for i, c in enumerate(chunks, start=1):
        if referenced is not None and i not in referenced:
            continue
        citations.append(
            Citation(
                document_id=c.document_id,
                chunk_id=c.chunk_id,
                title=c.title,
                authors=c.authors,
                page_number=c.page_number,
                section=c.section,
                snippet=c.content[:_SNIPPET_LEN].strip(),
                score=round(c.rerank_score or c.fused_score, 4),
            )
        )
    return citations


class AnswerGenerator:
    def __init__(self) -> None:
        self.llm = get_llm()

    async def generate(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        history: list[LLMMessage] | None = None,
    ) -> tuple[str, list[Citation], int]:
        messages = build_messages(query, chunks, history)
        resp = await self.llm.complete(messages, max_tokens=1024)
        citations = build_citations(chunks, resp.content)
        return resp.content, citations, resp.total_tokens

    async def stream(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        history: list[LLMMessage] | None = None,
    ) -> AsyncIterator[str]:
        messages = build_messages(query, chunks, history)
        async for delta in self.llm.stream(messages, max_tokens=1024):
            yield delta
