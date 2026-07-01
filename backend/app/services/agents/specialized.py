"""The four specialized agents. Each wraps existing services as a 'tool' and returns a
uniform AgentResponse so the orchestrator/UI can treat them the same way."""
from __future__ import annotations

from fastapi import HTTPException, status

from app.schemas.agent import AgentResponse, AgentStep, AgentType
from app.schemas.comparison import ComparisonRow
from app.services.agents.base import AgentContext, BaseAgent
from app.services.comparison import PaperComparator
from app.services.document_context import get_owned_ready_document, load_document_text
from app.services.rag import RAGPipeline
from app.services.rag.generator import build_citations
from app.services.summarization import Summarizer


class ResearchAgent(BaseAgent):
    name = AgentType.RESEARCH.value

    def __init__(self, rag: RAGPipeline) -> None:
        self.rag = rag

    async def run(self, query: str, ctx: AgentContext) -> AgentResponse:
        result = await self.rag.run(
            query,
            db=ctx.db,
            user_id=ctx.user_id,
            document_ids=ctx.document_id_strs,
            history=ctx.history,
        )
        return AgentResponse(
            agent=AgentType.RESEARCH,
            answer=result.answer,
            citations=result.citations,
            steps=[
                AgentStep(name="retrieve", detail=f"{len(result.citations)} sources"),
                AgentStep(name="generate", detail="grounded answer with citations"),
            ],
            tokens_used=result.tokens_used or 0,
        )


class SummaryAgent(BaseAgent):
    name = AgentType.SUMMARY.value

    def __init__(self, summarizer: Summarizer) -> None:
        self.summarizer = summarizer

    async def run(self, query: str, ctx: AgentContext) -> AgentResponse:
        if not ctx.document_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The summary agent needs a document to summarize.",
            )
        doc_id = ctx.document_ids[0]
        document = await get_owned_ready_document(ctx.db, doc_id, ctx.user_id)
        text = await load_document_text(ctx.db, doc_id)
        detailed, tokens = await self.summarizer.detailed(document.title, text)

        answer = (
            f"**{document.title}**\n\n"
            f"**Problem.** {detailed.problem}\n\n"
            f"**Methodology.** {detailed.methodology}\n\n"
            f"**Dataset.** {detailed.dataset}\n\n"
            f"**Model.** {detailed.model}\n\n"
            f"**Results.** {detailed.results}\n\n"
            f"**Limitations.** {detailed.limitations}"
        )
        return AgentResponse(
            agent=AgentType.SUMMARY,
            answer=answer,
            steps=[AgentStep(name="summarize", detail=f"detailed summary of {document.title}")],
            tokens_used=tokens,
        )


class CitationAgent(BaseAgent):
    name = AgentType.CITATION.value

    def __init__(self, rag: RAGPipeline) -> None:
        self.rag = rag

    async def run(self, query: str, ctx: AgentContext) -> AgentResponse:
        expanded, chunks = await self.rag._retrieve_and_rerank(
            query,
            db=ctx.db,
            user_id=str(ctx.user_id),
            document_ids=ctx.document_id_strs,
            history_text=None,
            top_k=None,
            rerank_top_n=None,
        )
        citations = build_citations(chunks)
        if not citations:
            answer = "I couldn't find supporting passages for that claim."
        else:
            lines = [
                f"[{i}] {c.title} — p.{c.page_number or '?'}, {c.section or 'n/a'}"
                for i, c in enumerate(citations, start=1)
            ]
            answer = "Supporting sources:\n" + "\n".join(lines)
        return AgentResponse(
            agent=AgentType.CITATION,
            answer=answer,
            citations=citations,
            steps=[AgentStep(name="retrieve", detail=f"{len(citations)} candidate sources")],
        )


class ComparisonAgent(BaseAgent):
    name = AgentType.COMPARISON.value

    def __init__(self, comparator: PaperComparator) -> None:
        self.comparator = comparator

    async def run(self, query: str, ctx: AgentContext) -> AgentResponse:
        if not ctx.document_ids or len(ctx.document_ids) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The comparison agent needs at least two documents.",
            )
        papers = []
        for doc_id in ctx.document_ids[:5]:
            document = await get_owned_ready_document(ctx.db, doc_id, ctx.user_id)
            text = await load_document_text(ctx.db, doc_id, max_chars=9_000)
            papers.append({"document_id": doc_id, "title": document.title, "text": text})

        dims = ["Objective", "Dataset", "Architecture", "Results", "Advantages", "Limitations"]
        rows, synthesis, tokens = await self.comparator.compare(papers, dims)
        answer = _render_comparison(papers, rows, synthesis)
        return AgentResponse(
            agent=AgentType.COMPARISON,
            answer=answer,
            steps=[AgentStep(name="compare", detail=f"{len(papers)} papers across {len(dims)} dimensions")],
            tokens_used=tokens,
        )


def _render_comparison(papers: list[dict], rows: list[ComparisonRow], synthesis: str) -> str:
    id_to_title = {str(p["document_id"]): p["title"] for p in papers}
    lines = ["## Comparison\n"]
    for row in rows:
        lines.append(f"### {row.dimension}")
        for doc_id, text in row.cells.items():
            lines.append(f"- **{id_to_title.get(doc_id, doc_id)}**: {text}")
        lines.append("")
    if synthesis:
        lines.append(f"**Synthesis.** {synthesis}")
    return "\n".join(lines)
