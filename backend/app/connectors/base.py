from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "fbclid", "mc_cid", "mc_eid"}


@dataclass
class Candidate:
    """A raw search hit before content fetch and AI analysis."""

    url: str
    title: str
    snippet: str = ""
    source: str = ""  # connector name, e.g. "govuk", "legislation", "tavily"
    publisher: str = ""  # organisation / domain
    published_at: datetime | None = None
    sector_hints: set[str] = field(default_factory=set)
    matched_queries: set[str] = field(default_factory=set)
    content: str = ""

    def merge(self, other: "Candidate") -> None:
        self.sector_hints |= other.sector_hints
        self.matched_queries |= other.matched_queries
        if not self.snippet and other.snippet:
            self.snippet = other.snippet
        if not self.published_at and other.published_at:
            self.published_at = other.published_at
        if len(other.title) > len(self.title):
            self.title = other.title
        if not self.publisher and other.publisher:
            self.publisher = other.publisher


def normalise_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in TRACKING_PARAMS]
    path = re.sub(r"/+$", "", parts.path) or "/"
    return urlunsplit((parts.scheme.lower() or "https", parts.netloc.lower(), path, urlencode(query), ""))


def domain_of(url: str) -> str:
    return urlsplit(url).netloc.lower().removeprefix("www.")
