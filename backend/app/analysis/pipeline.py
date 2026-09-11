"""Weekly pipeline: search -> fetch -> triage -> analyse -> overview -> persist."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from ..config import Settings
from ..connectors import Candidate, collect_candidates, enrich_candidates
from ..db import Digest, Item, RunLog, session_scope
from ..knowledge.sectors import SECTOR_IDS, gs1_signal_score
from .llm import LLMClient, LLMError, gather_limited
from .prompts import analysis_prompt, overview_prompt, system_prompt, triage_prompt
from .schemas import DigestOverview, ItemAnalysis, TriageResponse

log = logging.getLogger(__name__)

_run_lock = asyncio.Lock()


def compute_window(settings: Settings, now: datetime | None = None) -> tuple[datetime, datetime]:
    tz = ZoneInfo(settings.schedule_timezone)
    now = now or datetime.now(tz)
    return now - timedelta(days=settings.lookback_days), now


async def _triage(llm: LLMClient, settings: Settings, candidates: list[Candidate], start: datetime, end: datetime) -> list[tuple[Candidate, int, list[str]]]:
    system = system_prompt()
    indexed = list(enumerate(candidates))
    batches = [indexed[i : i + settings.llm_triage_batch_size] for i in range(0, len(indexed), settings.llm_triage_batch_size)]

    async def _one(batch):
        raw = await llm.complete_json(system, triage_prompt(batch, start, end), max_tokens=3000, temperature=0.0)
        return TriageResponse.model_validate(raw)

    results = await gather_limited([_one(b) for b in batches], limit=3)
    kept: list[tuple[Candidate, int, list[str]]] = []
    for batch, res in zip(batches, results):
        if isinstance(res, Exception):
            log.warning("triage batch failed: %s", res)
            continue
        by_index = {idx: c for idx, c in batch}
        for v in res.verdicts:
            cand = by_index.get(v.index)
            if cand and v.relevant and v.relevance_score >= min(settings.relevance_threshold, 50):
                kept.append((cand, v.relevance_score, v.sectors or sorted(cand.sector_hints)))
    kept.sort(key=lambda t: (t[1], gs1_signal_score(t[0].title + " " + t[0].content)), reverse=True)
    return kept[: settings.llm_max_items_to_analyse]


async def _analyse(llm: LLMClient, cand: Candidate, start: datetime, end: datetime) -> ItemAnalysis | None:
    try:
        raw = await llm.complete_json(system_prompt(), analysis_prompt(cand, start, end), max_tokens=4000, temperature=0.2)
        analysis = ItemAnalysis.model_validate(raw)
    except (LLMError, ValidationError, Exception) as exc:  # noqa: BLE001
        log.warning("analysis failed for %s: %s", cand.url, exc)
        return None
    if not any(l.url == cand.url for l in analysis.links):
        analysis.links.insert(0, {"url": cand.url, "label": f"Source: {cand.publisher or cand.url}", "kind": "primary"})  # type: ignore[arg-type]
        analysis = ItemAnalysis.model_validate(analysis.model_dump())
    return analysis


def _dedupe_analyses(rows: list[tuple[Candidate, ItemAnalysis]]) -> list[tuple[Candidate, ItemAnalysis]]:
    """Collapse items that describe the same change (same normalised title) keeping the best-scored one."""
    seen: dict[str, tuple[Candidate, ItemAnalysis]] = {}
    for cand, an in rows:
        key = "".join(ch for ch in an.title.lower() if ch.isalnum())[:60]
        if key not in seen or an.relevance_score > seen[key][1].relevance_score:
            seen[key] = (cand, an)
    return sorted(seen.values(), key=lambda r: r[1].relevance_score, reverse=True)


def _fallback_overview(items: list[dict]) -> DigestOverview:
    sector_overviews = []
    for sid in SECTOR_IDS:
        sector_items = [i for i in items if i["primary_sector"] == sid]
        sector_overviews.append(
            {
                "sector": sid,
                "headline": f"{len(sector_items)} relevant change(s) this week" if sector_items else "No relevant changes detected this week",
                "summary": " ".join(i["summary"] for i in sector_items[:3]) or "Nothing in this sector passed the relevance test this week.",
                "top_priorities": [i["title"] for i in sector_items[:4]],
                "watchlist": [],
            }
        )
    return DigestOverview(
        headline=f"{len(items)} regulatory changes relevant to GS1 UK this week",
        executive_summary="Automatic overview unavailable; see individual items.",
        cross_sector_themes=[],
        sector_overviews=sector_overviews,  # type: ignore[arg-type]
    )


async def run_weekly_digest(settings: Settings, *, trigger: str = "schedule", now: datetime | None = None) -> int:
    """Execute a full run and return the digest id. Concurrent runs are serialised."""
    if _run_lock.locked():
        raise RuntimeError("a digest run is already in progress")
    async with _run_lock:
        return await _run(settings, trigger=trigger, now=now)


async def _run(settings: Settings, *, trigger: str, now: datetime | None) -> int:
    start, end = compute_window(settings, now)
    with session_scope() as s:
        digest = Digest(window_start=start, window_end=end, status="running", trigger=trigger)
        s.add(digest)
        s.flush()
        run = RunLog(digest_id=digest.id, trigger=trigger)
        s.add(run)
        s.flush()
        digest_id, run_id = digest.id, run.id

    stats: dict = {}
    try:
        if not settings.llm_configured:
            raise LLMError("No LLM API key configured (set ANTHROPIC_API_KEY or OPENAI_API_KEY)")
        llm = LLMClient(settings)

        log.info("[%s] collecting candidates for %s -> %s", digest_id, start.date(), end.date())
        candidates, stats = await collect_candidates(settings, start, end)
        candidates.sort(key=lambda c: gs1_signal_score(c.title + " " + c.snippet), reverse=True)

        log.info("[%s] triaging %d candidates", digest_id, len(candidates))
        kept = await _triage(llm, settings, candidates, start, end)
        stats["triaged_relevant"] = len(kept)

        log.info("[%s] fetching content for %d items", digest_id, len(kept))
        await enrich_candidates(settings, [c for c, _, _ in kept])

        log.info("[%s] analysing %d items", digest_id, len(kept))
        analyses = await gather_limited([_analyse(llm, c, start, end) for c, _, _ in kept], limit=4)
        rows = [(c, a) for (c, _, _), a in zip(kept, analyses) if isinstance(a, ItemAnalysis) and a.relevance_score >= settings.relevance_threshold]
        rows = _dedupe_analyses(rows)
        stats["analysed"] = len(rows)

        with session_scope() as s:
            digest = s.get(Digest, digest_id)
            assert digest
            item_dicts = []
            for cand, an in rows:
                item = Item(
                    digest_id=digest_id,
                    url=cand.url,
                    title=an.title,
                    publisher=cand.publisher,
                    issuing_body=an.issuing_body,
                    published_at=cand.published_at,
                    change_type=an.change_type,
                    jurisdiction=an.jurisdiction,
                    sectors=an.sectors,
                    primary_sector=an.primary_sector,
                    impact=an.impact,
                    relevance_score=an.relevance_score,
                    summary=an.summary,
                    what_changed=an.what_changed,
                    why_it_matters_to_gs1=an.why_it_matters_to_gs1,
                    gs1_standards_implicated=an.gs1_standards_implicated,
                    affected_stakeholders=an.affected_stakeholders,
                    key_dates=[k.model_dump() for k in an.key_dates],
                    next_steps=[n.model_dump() for n in an.next_steps],
                    links=[l.model_dump() for l in an.links],
                    confidence=an.confidence,
                    source_connector=cand.source,
                )
                s.add(item)
                s.flush()
                item_dicts.append({"id": item.id, **an.model_dump()})

            try:
                overview = DigestOverview.model_validate(
                    await llm.complete_json(system_prompt(), overview_prompt(item_dicts, start, end), max_tokens=3500, temperature=0.3)
                ) if item_dicts else _fallback_overview(item_dicts)
            except Exception as exc:  # noqa: BLE001
                log.warning("overview generation failed: %s", exc)
                overview = _fallback_overview(item_dicts)

            digest.headline = overview.headline
            digest.executive_summary = overview.executive_summary
            digest.cross_sector_themes = overview.cross_sector_themes
            digest.sector_overviews = [o.model_dump() for o in overview.sector_overviews]
            digest.stats = stats
            digest.status = "completed"
            digest.completed_at = datetime.now(end.tzinfo)
            run = s.get(RunLog, run_id)
            if run:
                run.status, run.finished_at, run.stats = "completed", digest.completed_at, stats
                run.message = f"{len(rows)} items analysed from {stats.get('unique', 0)} unique candidates"
        log.info("[%s] digest completed with %d items", digest_id, len(rows))
        return digest_id

    except Exception as exc:  # noqa: BLE001
        log.exception("digest run %s failed", digest_id)
        with session_scope() as s:
            digest = s.get(Digest, digest_id)
            if digest:
                digest.status, digest.error, digest.stats = "failed", str(exc), stats
                digest.completed_at = datetime.now(end.tzinfo)
            run = s.get(RunLog, run_id)
            if run:
                run.status, run.message, run.finished_at, run.stats = "failed", str(exc), datetime.now(end.tzinfo), stats
        raise
