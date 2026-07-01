from __future__ import annotations

import uuid
from enum import Enum

from pydantic import BaseModel, Field


class SummaryType(str, Enum):
    SHORT = "short"
    DETAILED = "detailed"


class SummaryRequest(BaseModel):
    summary_type: SummaryType = SummaryType.SHORT


class DetailedSummary(BaseModel):
    problem: str = ""
    methodology: str = ""
    dataset: str = ""
    model: str = ""
    results: str = ""
    limitations: str = ""


class SummaryResponse(BaseModel):
    document_id: uuid.UUID
    summary_type: SummaryType
    short_summary: str | None = None
    detailed_summary: DetailedSummary | None = None
    tokens_used: int = 0
