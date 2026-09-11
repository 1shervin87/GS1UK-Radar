"""Search connectors: GOV.UK, legislation.gov.uk and general web search."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

import httpx

from ..config import Settings
from ..knowledge.sectors import all_queries, guess_sectors
from .base import Candidate, normalise_url
from .fetcher import fetch_all, within_window
from .govuk import search_govuk
from .legislation import fetch_new_legislation
from .websearch import search_web

log = logging.getLogger(__name__)


async def collect_candidates(settings: Settings, since: datetime, until: datetime) -> tuple[list[Candidate], dict[str, int]]:
    """Run every query across every enabled connector and return de-duplicated candidates."""
    queries = all_queries()
    found: dict[str, Candidate] = {}
    stats = {"queries": len(queries), "govuk": 0, "legislation": 0, "web": 0, "raw_hits": 0, "unique": 0}

    def _absorb(results: list[Candidate], sector_hint: str | None, query: str, bucket: str) -> None:
        for cand in results:
            stats["raw_hits"] += 1
            stats[bucket] += 1
            if not within_window(cand.published_at, since):
                continue
            key = normalise_url(cand.url)
            cand.url = key
            if sector_hint:
                cand.sector_hints.add(sector_hint)
            cand.sector_hints |= set(guess_sectors(f"{cand.title} {cand.snippet}"))
            cand.matched_queries.add(query)
            if key in found:
                found[key].merge(cand)
            else:
                found[key] = cand

    async with httpx.AsyncClient(timeout=settings.fetch_timeout_seconds, headers={"Accept": "application/json, application/atom+xml;q=0.9, */*;q=0.8"}) as client:
        if settings.enable_legislation_feed:
            _absorb(await fetch_new_legislation(client, since, until), None, "legislation.gov.uk new legislation", "legislation")

        sem = asyncio.Semaphore(4)

        async def _run_query(sector_hint: str | None, query: str) -> None:
            async with sem:
                if settings.enable_govuk_search:
                    _absorb(await search_govuk(client, query, since, settings.max_results_per_query), sector_hint, query, "govuk")
                if settings.enable_web_search:
                    _absorb(await search_web(settings, query, since), sector_hint, query, "web")

        await asyncio.gather(*(_run_query(s, q) for s, q in queries), return_exceptions=True)

    candidates = list(found.values())
    stats["unique"] = len(candidates)
    log.info("collected %d unique candidates from %d raw hits", len(candidates), stats["raw_hits"])
    return candidates, stats


async def enrich_candidates(settings: Settings, candidates: list[Candidate]) -> None:
    await fetch_all(
        candidates,
        concurrency=settings.fetch_concurrency,
        timeout=settings.fetch_timeout_seconds,
        max_chars=settings.max_article_chars,
    )


__all__ = ["Candidate", "collect_candidates", "enrich_candidates"]
