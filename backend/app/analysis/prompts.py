from __future__ import annotations

import json
from datetime import datetime

from ..connectors.base import Candidate
from ..knowledge.sectors import load_context_brief

SYSTEM_BASE = """You are the regulatory intelligence analyst for GS1 UK. You monitor UK (and UK-affecting EU/international) regulatory, legislative, policy and major industry-scheme changes across retail, construction and healthcare, and explain precisely why each change matters to GS1 UK and its members.

You must ground every judgement in the reference brief below. Be sceptical: most news is NOT relevant. Only flag items that pass the relevance test in section 3 of the brief. Never invent facts, dates or URLs; if the source does not state something, say so or omit it. Respond ONLY with valid JSON matching the requested schema, no prose before or after.

=== GS1 UK REFERENCE BRIEF ===
{brief}
=== END BRIEF ===
"""


def system_prompt() -> str:
    return SYSTEM_BASE.format(brief=load_context_brief())


def triage_prompt(batch: list[tuple[int, Candidate]], window_start: datetime, window_end: datetime) -> str:
    rows = []
    for idx, c in batch:
        rows.append(
            {
                "index": idx,
                "title": c.title[:200],
                "publisher": c.publisher,
                "published_at": c.published_at.isoformat() if c.published_at else None,
                "url": c.url,
                "snippet": (c.snippet or c.content[:400])[:500],
                "sector_hints": sorted(c.sector_hints),
            }
        )
    return f"""Monitoring window: {window_start.date().isoformat()} to {window_end.date().isoformat()}.

Triage the following search hits. For each, decide whether it is a regulatory/legislative/policy/major-scheme change (or an authoritative update about one) that is relevant to GS1 UK per the relevance test, and which sector(s) it belongs to. Score relevance 0–100 (100 = directly mandates identifiers/barcodes/data sharing in a GS1 UK sector). Mark items relevant only if score >= 50. Duplicates of the same underlying change should still each be marked; de-duplication happens later. Items clearly outside the window or purely commercial/marketing content should be marked not relevant.

Return JSON: {{"verdicts": [{{"index": int, "relevant": bool, "relevance_score": int, "sectors": ["retail"|"construction"|"healthcare"], "reason": "<=25 words"}}]}}

Hits:
{json.dumps(rows, ensure_ascii=False, indent=1)}
"""


def analysis_prompt(c: Candidate, window_start: datetime, window_end: datetime) -> str:
    body = c.content or c.snippet or "(no article text could be extracted; rely on title and snippet only and lower your confidence)"
    return f"""Monitoring window: {window_start.date().isoformat()} to {window_end.date().isoformat()}.

Analyse this item for GS1 UK. Explain the change itself, then analyse why it is relevant to GS1 UK (be specific: which GS1 identifiers, data carriers, data-sharing standards, services or programmes are implicated and how), who is affected, key dates, and recommended next steps for GS1 UK as an organisation and for affected GS1 UK members. Only include links that appear in the source material or that are the source URL itself. If the item does not actually describe a regulatory/policy/scheme change relevant to GS1 UK, set relevance_score below 50 and explain briefly in why_it_matters_to_gs1.

Return JSON with exactly these keys:
{{
  "title": "clear, specific headline (<=110 chars)",
  "issuing_body": "e.g. MHRA, MHCLG, Defra, Exchange for Change, European Commission",
  "change_type": "legislation|draft_legislation|consultation|guidance|policy|enforcement|standard|industry_scheme|eu_international|nhs_programme|other",
  "jurisdiction": "UK|GB|England|Scotland|Wales|Northern Ireland|EU (affects UK)|International (affects UK)",
  "sectors": ["retail"|"construction"|"healthcare", ...],
  "primary_sector": "retail|construction|healthcare",
  "impact": "high|medium|low",
  "relevance_score": 0-100,
  "summary": "2-3 sentence plain-English summary of the change",
  "what_changed": "factual paragraph(s): what was published/decided, by whom, when, scope, obligations, timelines",
  "why_it_matters_to_gs1": "analytical paragraph(s): the explicit connection to GS1 UK - identification keys (GTIN/GLN/SSCC/GSRN/UDI...), data carriers (EAN/UPC, GS1 DataMatrix, QR codes powered by GS1 / GS1 Digital Link), data sharing (GDSN/productDNA, EPCIS, e-invoicing/PEPPOL), programmes (Sunrise 2027, DRS readiness, Scan4Safety, DPP readiness, golden thread); risks/opportunities for GS1 UK and members; what would happen if members do nothing",
  "gs1_standards_implicated": ["GTIN", "GS1 Digital Link", ...],
  "affected_stakeholders": ["e.g. drinks producers", "NHS trusts", "construction product manufacturers"],
  "key_dates": [{{"date": "YYYY-MM-DD or text", "label": "what happens"}}],
  "next_steps": [{{"audience": "gs1_uk|members|both", "action": "specific, actionable step", "priority": "now|next_quarter|monitor"}}],
  "links": [{{"url": "...", "label": "...", "kind": "primary|official|guidance|gs1|news|other"}}],
  "confidence": "high|medium|low"
}}

SOURCE
Title: {c.title}
Publisher: {c.publisher}
Published: {c.published_at.isoformat() if c.published_at else "unknown"}
URL: {c.url}
Matched search queries: {sorted(c.matched_queries)[:6]}

ARTICLE TEXT
{body}
"""


def overview_prompt(items: list[dict], window_start: datetime, window_end: datetime) -> str:
    compact = [
        {
            "id": it["id"],
            "title": it["title"],
            "sectors": it["sectors"],
            "primary_sector": it["primary_sector"],
            "impact": it["impact"],
            "relevance_score": it["relevance_score"],
            "issuing_body": it["issuing_body"],
            "summary": it["summary"],
            "key_dates": it["key_dates"][:3],
        }
        for it in items
    ]
    return f"""Monitoring window: {window_start.date().isoformat()} to {window_end.date().isoformat()}.

Write the weekly executive overview for GS1 UK's leadership and sector teams based ONLY on the analysed items below. Produce an overall headline and executive summary (what this week means for GS1 UK, 4-6 sentences), 2-5 cross-sector themes, and for EACH of the three sectors (retail, construction, healthcare) a headline, a 3-5 sentence summary, top priorities (max 4, each referencing the relevant item title) and a short watchlist. If a sector has no items this week, say so plainly and suggest what to watch based on the reference brief.

Return JSON:
{{
  "headline": "...",
  "executive_summary": "...",
  "cross_sector_themes": ["..."],
  "sector_overviews": [
    {{"sector": "retail", "headline": "...", "summary": "...", "top_priorities": ["..."], "watchlist": ["..."]}},
    {{"sector": "construction", ...}},
    {{"sector": "healthcare", ...}}
  ]
}}

ITEMS
{json.dumps(compact, ensure_ascii=False, indent=1)}
"""
