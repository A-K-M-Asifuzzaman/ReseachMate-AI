from __future__ import annotations

from app.schemas.agent import AgentResponse, AgentStep, AgentType
from app.services.agents.base import AgentContext
from app.services.agents.planner import Planner
from app.services.agents.specialized import (
    CitationAgent,
    ComparisonAgent,
    ResearchAgent,
    SummaryAgent,
)
from app.services.comparison import PaperComparator
from app.services.rag import RAGPipeline
from app.services.summarization import Summarizer


class AgentOrchestrator:
    """Plans which agent to use (unless forced) and dispatches to it.

    Workflow: Planner → chosen Agent → (Tools → Retriever → Answer generator).
    """

    def __init__(self) -> None:
        rag = RAGPipeline()
        summarizer = Summarizer()
        comparator = PaperComparator()

        self.planner = Planner()
        self._agents = {
            AgentType.RESEARCH: ResearchAgent(rag),
            AgentType.SUMMARY: SummaryAgent(summarizer),
            AgentType.CITATION: CitationAgent(rag),
            AgentType.COMPARISON: ComparisonAgent(comparator),
        }

    async def run(
        self, query: str, ctx: AgentContext, *, forced: AgentType | None = None
    ) -> AgentResponse:
        if forced is not None:
            chosen, reason = forced, "explicitly requested"
        else:
            chosen, reason = await self.planner.plan(
                query, num_documents=len(ctx.document_ids or [])
            )

        agent = self._agents[chosen]
        response = await agent.run(query, ctx)
        # Prepend the planning step for transparency.
        response.steps.insert(
            0, AgentStep(name="plan", detail=f"selected {chosen.value} agent — {reason}")
        )
        return response
