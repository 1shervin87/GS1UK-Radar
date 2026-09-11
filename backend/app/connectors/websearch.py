"""General web search: Tavily when an API key is configured, DuckDuckGo otherwise.

Both are called with a UK bias and a one-week recency window. Tavily is preferred because it
returns article dates and supports domain hints; DuckDuckGo is a keyless fallback so the
pipeline still works without any paid search provider.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from dateutil import parser as dateparser

from ..config import Settings
from .base import Candidate, domain_of

log = logging.getLogger(__name__)

# Authoritative UK domains that should be favoured when the provider supports it.
PRIORITY_DOMAINS = [
    "gov.uk", "legislation.gov.uk", "parliament.uk", "nhs.uk", "england.nhs.uk", "supplychain.nhs.uk",
    "scan4safety.nhs.uk", "gs1uk.org", "gs1.org", "bsigroup.com", "exchangeforchange.org.uk",
    "cpa.org.uk", "abhi.org.uk", "brc.org.uk", "fdf.org.uk", "food.gov.uk", "hse.gov.uk",
    "europa.eu", "thegrocer.co.uk", "retail-week.com", "constructionnews.co.uk", "building.co.uk",
    "digitalhealth.net", "hsj.co.uk", "pharmaceutical-journal.com", "medtechnews.uk",
]


def _uk_bias(query: str) -> str:
    lowered = query.lower()
    if any(tok in lowered for tok in (" uk", "uk ", "britain", "england", "nhs", "mhra", "gs1 uk", "scotland", "wales", "northern ireland")):
        return query
    return f"{query} UK"


async def search_tavily(settings: Settings, query: str, since: datetime, max_results: int) -> list[Candidate]:
    from tavily import TavilyClient  # imported lazily so the dependency is optional at runtime

    client = TavilyClient(api_key=settings.tavily_api_key)
    days = max(1, (datetime.now(since.tzinfo) - since).days + 1)

    def _call():
        return client.search(
            query=_uk_bias(query),
            search_depth="advanced",
            topic="news",
            days=days,
            max_results=max_results,
            include_answer=False,
            include_raw_content=False,
        )

    try:
        data = await asyncio.to_thread(_call)
    except Exception as exc:  # noqa: BLE001 - provider errors are non-fatal
        log.warning("Tavily search failed for %r: %s", query, exc)
        return []

    out: list[Candidate] = []
    for row in data.get("results", []):
        url = row.get("url")
        if not url:
            continue
        published = None
        if row.get("published_date"):
            try:
                published = dateparser.parse(row["published_date"])
            except (ValueError, TypeError):
                published = None
        out.append(
            Candidate(
                url=url,
                title=row.get("title") or url,
                snippet=(row.get("content") or "")[:600],
                source="tavily",
                publisher=domain_of(url),
                published_at=published,
            )
        )
    return out


async def search_duckduckgo(query: str, max_results: int) -> list[Candidate]:
    from duckduckgo_search import DDGS

    def _call():
        with DDGS() as ddgs:
            news = list(ddgs.news(_uk_bias(query), region="uk-en", timelimit="w", max_results=max_results))
            if len(news) < max_results // 2:
                news += list(ddgs.text(_uk_bias(query), region="uk-en", timelimit="w", max_results=max_results))
            return news

    try:
        rows = await asyncio.to_thread(_call)
    except Exception as exc:  # noqa: BLE001
        log.warning("DuckDuckGo search failed for %r: %s", query, exc)
        return []

    out: list[Candidate] = []
    for row in rows:
        url = row.get("url") or row.get("href")
        if not url:
            continue
        published = None
        if row.get("date"):
            try:
                published = dateparser.parse(row["date"])
            except (ValueError, TypeError):
                published = None
        out.append(
            Candidate(
                url=url,
                title=row.get("title") or url,
                snippet=(row.get("body") or "")[:600],
                source="duckduckgo",
                publisher=row.get("source") or domain_of(url),
                published_at=published,
            )
        )
    return out


async def search_web(settings: Settings, query: str, since: datetime) -> list[Candidate]:
    if settings.tavily_api_key:
        return await search_tavily(settings, query, since, settings.max_results_per_query)
    return await search_duckduckgo(query, settings.max_results_per_query)
