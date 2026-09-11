"""GOV.UK Search API connector (no API key required).

Docs: https://docs.publishing.service.gov.uk/repos/search-api/using-the-search-api.html
"""

from __future__ import annotations

import logging
from datetime import datetime

import httpx
from dateutil import parser as dateparser

from .base import Candidate

log = logging.getLogger(__name__)

SEARCH_URL = "https://www.gov.uk/api/search.json"

# Document types that represent regulatory / policy signal rather than noise (e.g. speeches, jobs).
PREFERRED_TYPES = {
    "consultation", "open_consultation", "closed_consultation", "consultation_outcome",
    "guidance", "detailed_guide", "policy_paper", "impact_assessment", "regulation",
    "notice", "press_release", "news_story", "statutory_guidance", "correspondence",
    "publication", "official_statistics", "form", "government_response", "call_for_evidence",
    "decision", "standard", "research", "independent_report", "world_news_story",
}


async def search_govuk(client: httpx.AsyncClient, query: str, since: datetime, count: int = 10) -> list[Candidate]:
    params = {
        "q": query,
        "count": str(count),
        "order": "-public_timestamp",
        "filter_public_timestamp": f"from:{since.date().isoformat()}",
        "fields": "title,description,link,public_timestamp,organisations,content_store_document_type",
    }
    try:
        resp = await client.get(SEARCH_URL, params=params)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning("GOV.UK search failed for %r: %s", query, exc)
        return []

    out: list[Candidate] = []
    for row in resp.json().get("results", []):
        link = row.get("link") or ""
        if not link:
            continue
        url = link if link.startswith("http") else f"https://www.gov.uk{link}"
        doc_type = row.get("content_store_document_type") or ""
        if doc_type and doc_type not in PREFERRED_TYPES and doc_type not in {"html_publication", "answer"}:
            continue
        published = None
        if row.get("public_timestamp"):
            try:
                published = dateparser.isoparse(row["public_timestamp"])
            except (ValueError, TypeError):
                published = None
        orgs = row.get("organisations") or []
        publisher = ", ".join(o.get("title", "") for o in orgs if isinstance(o, dict) and o.get("title")) or "GOV.UK"
        out.append(
            Candidate(
                url=url,
                title=row.get("title") or url,
                snippet=(row.get("description") or "").strip(),
                source="govuk",
                publisher=publisher,
                published_at=published,
            )
        )
    return out
