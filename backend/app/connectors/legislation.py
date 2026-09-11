"""legislation.gov.uk "new legislation" Atom feeds (no API key required).

`https://www.legislation.gov.uk/new/<YYYY-MM-DD>/data.feed` lists every piece of legislation
published on that day. We pull each day in the lookback window and keep items whose title
matches sector keywords, so the analysis agent sees newly laid statutory instruments.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

import feedparser
import httpx
from dateutil import parser as dateparser

from ..knowledge.sectors import GS1_KEYWORDS, SECTORS
from .base import Candidate

log = logging.getLogger(__name__)

FEED_URL = "https://www.legislation.gov.uk/new/{day}/data.feed"

TITLE_KEYWORDS = tuple(
    sorted(
        set(GS1_KEYWORDS)
        | {k for s in SECTORS.values() for k in s.keywords}
        | {
            "product", "packaging", "deposit", "medical", "medicines", "devices", "building",
            "construction", "food", "health", "safety", "consumer", "trade", "goods", "supply",
            "invoic", "market surveillance", "border", "import", "export", "waste", "recycling",
        }
    )
)


def _matches(title: str) -> bool:
    lowered = title.lower()
    return any(k in lowered for k in TITLE_KEYWORDS)


async def fetch_new_legislation(client: httpx.AsyncClient, since: datetime, until: datetime | None = None) -> list[Candidate]:
    until = until or datetime.now(timezone.utc)
    day: date = since.date()
    out: list[Candidate] = []
    while day <= until.date():
        url = FEED_URL.format(day=day.isoformat())
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                feed = feedparser.parse(resp.text)
                for entry in feed.entries:
                    title = getattr(entry, "title", "") or ""
                    if not _matches(title):
                        continue
                    link = getattr(entry, "link", "") or getattr(entry, "id", "")
                    if not link:
                        continue
                    link = link.replace("http://", "https://", 1).removesuffix("/data.htm")
                    published = None
                    for attr in ("published", "updated"):
                        raw = getattr(entry, attr, None)
                        if raw:
                            try:
                                published = dateparser.parse(raw)
                                break
                            except (ValueError, TypeError):
                                continue
                    out.append(
                        Candidate(
                            url=link,
                            title=title,
                            snippet=(getattr(entry, "summary", "") or "")[:500],
                            source="legislation",
                            publisher="legislation.gov.uk",
                            published_at=published or datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc),
                        )
                    )
            elif resp.status_code != 404:
                log.warning("legislation.gov.uk feed %s returned %s", url, resp.status_code)
        except httpx.HTTPError as exc:
            log.warning("legislation.gov.uk feed failed for %s: %s", day, exc)
        day += timedelta(days=1)
    return out
