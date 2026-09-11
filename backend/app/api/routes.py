from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..config import Settings, get_settings
from ..db import Digest, Item, RunLog, get_session
from ..knowledge.sectors import SECTOR_IDS, SECTORS
from .schemas import (
    DigestOut,
    DigestSummaryOut,
    ItemOut,
    ItemSummaryOut,
    RunRequest,
    RunResponse,
    SectorCount,
    SectorInfo,
    StatusOut,
)

router = APIRouter(prefix="/api")

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def _sector_counts(items: list[Item]) -> list[SectorCount]:
    out = []
    for sid in SECTOR_IDS:
        in_sector = [i for i in items if sid in (i.sectors or []) or i.primary_sector == sid]
        out.append(SectorCount(sector=sid, total=len(in_sector), high=sum(1 for i in in_sector if i.impact == "high")))
    return out


def _digest_summary(d: Digest) -> DigestSummaryOut:
    return DigestSummaryOut(
        id=d.id,
        window_start=d.window_start,
        window_end=d.window_end,
        created_at=d.created_at,
        completed_at=d.completed_at,
        status=d.status,
        trigger=d.trigger,
        headline=d.headline,
        is_sample=d.is_sample,
        item_count=len(d.items),
        sector_counts=_sector_counts(d.items),
    )


def _digest_out(d: Digest) -> DigestOut:
    base = _digest_summary(d).model_dump()
    return DigestOut(
        **base,
        executive_summary=d.executive_summary,
        cross_sector_themes=d.cross_sector_themes or [],
        sector_overviews=d.sector_overviews or [],
        stats=d.stats or {},
        error=d.error,
        items=[ItemSummaryOut.model_validate(i) for i in d.items],
    )


def _latest_completed(session: Session) -> Digest | None:
    stmt = (
        select(Digest)
        .options(selectinload(Digest.items))
        .where(Digest.status == "completed")
        .order_by(Digest.window_end.desc(), Digest.id.desc())
        .limit(1)
    )
    return session.execute(stmt).scalars().first()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/status", response_model=StatusOut)
def status(request: Request, session: SessionDep, settings: SettingsDep) -> StatusOut:
    sched = request.app.state.scheduler
    latest = _latest_completed(session)
    return StatusOut(
        app=settings.app_name,
        environment=settings.environment,
        llm_provider=settings.llm_provider,
        llm_configured=settings.llm_configured,
        web_search_provider="tavily" if settings.tavily_api_key else "duckduckgo",
        schedule=sched.cron_description,
        timezone=settings.schedule_timezone,
        next_run=sched.next_run,
        running=sched.running,
        latest_digest_id=latest.id if latest else None,
        sectors=[SectorInfo(id=s.id, name=s.name, colour=s.colour, description=s.description) for s in SECTORS.values()],
    )


@router.get("/sectors", response_model=list[SectorInfo])
def sectors() -> list[SectorInfo]:
    return [SectorInfo(id=s.id, name=s.name, colour=s.colour, description=s.description) for s in SECTORS.values()]


@router.get("/digests", response_model=list[DigestSummaryOut])
def list_digests(session: SessionDep, limit: int = Query(26, le=200)) -> list[DigestSummaryOut]:
    stmt = select(Digest).options(selectinload(Digest.items)).order_by(Digest.window_end.desc(), Digest.id.desc()).limit(limit)
    return [_digest_summary(d) for d in session.execute(stmt).scalars().all()]


@router.get("/digests/latest", response_model=DigestOut)
def latest_digest(session: SessionDep) -> DigestOut:
    d = _latest_completed(session)
    if not d:
        raise HTTPException(404, "No completed digest yet")
    return _digest_out(d)


@router.get("/digests/{digest_id}", response_model=DigestOut)
def get_digest(digest_id: int, session: SessionDep) -> DigestOut:
    d = session.execute(select(Digest).options(selectinload(Digest.items)).where(Digest.id == digest_id)).scalars().first()
    if not d:
        raise HTTPException(404, "Digest not found")
    return _digest_out(d)


@router.get("/digests/{digest_id}/items", response_model=list[ItemSummaryOut])
def digest_items(digest_id: int, session: SessionDep, sector: str | None = None, impact: str | None = None) -> list[ItemSummaryOut]:
    if sector and sector not in SECTOR_IDS:
        raise HTTPException(400, f"unknown sector {sector!r}")
    stmt = select(Item).where(Item.digest_id == digest_id).order_by(Item.relevance_score.desc())
    items = session.execute(stmt).scalars().all()
    if sector:
        items = [i for i in items if sector in (i.sectors or []) or i.primary_sector == sector]
    if impact:
        items = [i for i in items if i.impact == impact]
    return [ItemSummaryOut.model_validate(i) for i in items]


@router.get("/items/{item_id}", response_model=ItemOut)
def get_item(item_id: int, session: SessionDep) -> ItemOut:
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    return ItemOut.model_validate(item)


@router.get("/items", response_model=list[ItemSummaryOut])
def search_items(
    session: SessionDep,
    q: str | None = None,
    sector: str | None = None,
    limit: int = Query(50, le=200),
) -> list[ItemSummaryOut]:
    stmt = select(Item).join(Digest).where(Digest.status == "completed").order_by(Item.created_at.desc(), Item.relevance_score.desc())
    if q:
        pattern = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(Item.title).like(pattern) | func.lower(Item.summary).like(pattern) | func.lower(Item.why_it_matters_to_gs1).like(pattern))
    items = session.execute(stmt.limit(limit * 3)).scalars().all()
    if sector:
        items = [i for i in items if sector in (i.sectors or []) or i.primary_sector == sector]
    return [ItemSummaryOut.model_validate(i) for i in items[:limit]]


@router.get("/runs")
def runs(session: SessionDep, limit: int = Query(20, le=100)) -> list[dict]:
    rows = session.execute(select(RunLog).order_by(RunLog.started_at.desc()).limit(limit)).scalars().all()
    return [
        {
            "id": r.id,
            "digest_id": r.digest_id,
            "started_at": r.started_at,
            "finished_at": r.finished_at,
            "status": r.status,
            "trigger": r.trigger,
            "message": r.message,
            "stats": r.stats,
        }
        for r in rows
    ]


def _require_admin(settings: Settings, authorization: str | None) -> None:
    if not settings.admin_token:
        raise HTTPException(403, "ADMIN_TOKEN is not configured; manual runs are disabled")
    if authorization != f"Bearer {settings.admin_token}":
        raise HTTPException(401, "Invalid admin token")


@router.post("/admin/run", response_model=RunResponse)
def trigger_run(
    request: Request,
    settings: SettingsDep,
    body: RunRequest | None = None,
    authorization: Annotated[str | None, Header()] = None,
) -> RunResponse:
    _require_admin(settings, authorization)
    if not settings.llm_configured:
        raise HTTPException(400, "No LLM API key configured; cannot run analysis")
    started = request.app.state.scheduler.trigger("manual", lookback_days=body.lookback_days if body else None)
    return RunResponse(started=started, message="Digest run started" if started else "A run is already in progress")
