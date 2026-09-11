from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Sector = Literal["retail", "construction", "healthcare"]
Impact = Literal["high", "medium", "low"]
ChangeType = Literal[
    "legislation", "draft_legislation", "consultation", "guidance", "policy", "enforcement",
    "standard", "industry_scheme", "eu_international", "nhs_programme", "other",
]


class TriageVerdict(BaseModel):
    index: int
    relevant: bool
    relevance_score: int = Field(ge=0, le=100)
    sectors: list[Sector] = []
    reason: str = ""


class TriageResponse(BaseModel):
    verdicts: list[TriageVerdict]


class KeyDate(BaseModel):
    date: str  # ISO date or free text such as "Q4 2026"
    label: str


class Link(BaseModel):
    url: str
    label: str
    kind: Literal["primary", "official", "guidance", "gs1", "news", "other"] = "other"


class NextStep(BaseModel):
    audience: Literal["gs1_uk", "members", "both"] = "both"
    action: str
    priority: Literal["now", "next_quarter", "monitor"] = "next_quarter"


class ItemAnalysis(BaseModel):
    title: str
    issuing_body: str = ""
    change_type: ChangeType = "other"
    jurisdiction: str = "UK"
    sectors: list[Sector]
    primary_sector: Sector
    impact: Impact
    relevance_score: int = Field(ge=0, le=100)
    summary: str  # 2–3 sentence plain-English summary
    what_changed: str  # factual description of the change
    why_it_matters_to_gs1: str  # the analytical core
    gs1_standards_implicated: list[str] = []
    affected_stakeholders: list[str] = []
    key_dates: list[KeyDate] = []
    next_steps: list[NextStep] = []
    links: list[Link] = []
    confidence: Literal["high", "medium", "low"] = "medium"

    @field_validator("sectors")
    @classmethod
    def _non_empty(cls, v: list[Sector]) -> list[Sector]:
        if not v:
            raise ValueError("at least one sector required")
        return list(dict.fromkeys(v))


class SectorOverview(BaseModel):
    sector: Sector
    headline: str
    summary: str
    top_priorities: list[str] = []
    watchlist: list[str] = []


class DigestOverview(BaseModel):
    headline: str
    executive_summary: str
    cross_sector_themes: list[str] = []
    sector_overviews: list[SectorOverview]
