from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    digest_id: int
    url: str
    title: str
    publisher: str
    issuing_body: str
    published_at: datetime | None
    change_type: str
    jurisdiction: str
    sectors: list[str]
    primary_sector: str
    impact: str
    relevance_score: int
    summary: str
    what_changed: str
    why_it_matters_to_gs1: str
    gs1_standards_implicated: list[str]
    affected_stakeholders: list[str]
    key_dates: list[dict]
    next_steps: list[dict]
    links: list[dict]
    confidence: str
    source_connector: str


class ItemSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    digest_id: int
    title: str
    issuing_body: str
    publisher: str
    published_at: datetime | None
    change_type: str
    sectors: list[str]
    primary_sector: str
    impact: str
    relevance_score: int
    summary: str
    gs1_standards_implicated: list[str]
    key_dates: list[dict]


class SectorCount(BaseModel):
    sector: str
    total: int
    high: int


class DigestSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    window_start: datetime
    window_end: datetime
    created_at: datetime
    completed_at: datetime | None
    status: str
    trigger: str
    headline: str
    is_sample: bool
    item_count: int = 0
    sector_counts: list[SectorCount] = []


class DigestOut(DigestSummaryOut):
    executive_summary: str
    cross_sector_themes: list[str]
    sector_overviews: list[dict]
    stats: dict
    error: str | None
    items: list[ItemSummaryOut]


class SectorInfo(BaseModel):
    id: str
    name: str
    colour: str
    description: str


class StatusOut(BaseModel):
    app: str
    environment: str
    llm_provider: str
    llm_configured: bool
    web_search_provider: str
    schedule: str
    timezone: str
    next_run: datetime | None
    running: bool
    latest_digest_id: int | None
    sectors: list[SectorInfo]


class RunRequest(BaseModel):
    lookback_days: int | None = None


class RunResponse(BaseModel):
    started: bool
    message: str
