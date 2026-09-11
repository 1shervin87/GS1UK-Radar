"""Fetch candidate pages and extract readable article text."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

import httpx
import trafilatura
from dateutil import parser as dateparser

from .base import Candidate

log = logging.getLogger(__name__)

USER_AGENT = "GS1UK-RegulatoryRadar/1.0 (+https://www.gs1uk.org; weekly regulatory monitoring bot)"


async def fetch_content(client: httpx.AsyncClient, cand: Candidate, max_chars: int) -> None:
    try:
        resp = await client.get(cand.url, follow_redirects=True, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        log.debug("fetch failed %s: %s", cand.url, exc)
        return

    content_type = resp.headers.get("content-type", "")
    if "pdf" in content_type:
        return  # PDFs are analysed from their snippet/title only
    html = resp.text
    extracted = await asyncio.to_thread(
        trafilatura.extract,
        html,
        url=cand.url,
        include_comments=False,
        include_tables=True,
        favor_recall=True,
        with_metadata=False,
    )
    if extracted:
        cand.content = extracted[:max_chars]
    if not cand.published_at:
        meta = await asyncio.to_thread(trafilatura.extract_metadata, html, cand.url)
        if meta and meta.date:
            try:
                cand.published_at = dateparser.parse(meta.date)
            except (ValueError, TypeError):
                pass
    if not cand.publisher:
        cand.publisher = resp.url.host or ""


async def fetch_all(candidates: list[Candidate], *, concurrency: int, timeout: float, max_chars: int) -> None:
    semaphore = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(timeout=timeout) as client:

        async def _one(c: Candidate) -> None:
            async with semaphore:
                await fetch_content(client, c, max_chars)

        await asyncio.gather(*(_one(c) for c in candidates), return_exceptions=True)


def within_window(published: datetime | None, since: datetime) -> bool:
    if published is None:
        return True  # unknown date: keep and let the LLM judge from content
    if published.tzinfo is None:
        published = published.replace(tzinfo=since.tzinfo)
    return published >= since
