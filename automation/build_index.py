#!/usr/bin/env python3
"""Validate weekly digest JSON files and rebuild the static data index.

Usage (from the repository root):
    python automation/build_index.py            # validate everything, rebuild index.json + latest.json
    python automation/build_index.py --check    # validate only, exit 1 on problems

Standard library only, so the Cursor Automation agent can run it anywhere.

Layout:
    frontend/public/data/digests/<YYYY-MM-DD>.json   one file per weekly run (id = window end date)
    frontend/public/data/index.json                  generated
    frontend/public/data/latest.json                 generated (copy of newest completed digest)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "frontend" / "public" / "data"
DIGEST_DIR = DATA_DIR / "digests"

SECTORS = ("retail", "construction", "healthcare")
IMPACTS = ("high", "medium", "low")
CHANGE_TYPES = (
    "legislation", "draft_legislation", "consultation", "guidance", "policy", "enforcement",
    "standard", "industry_scheme", "eu_international", "nhs_programme", "other",
)
LINK_KINDS = ("primary", "official", "guidance", "gs1", "news", "other")
AUDIENCES = ("gs1_uk", "members", "both")
PRIORITIES = ("now", "next_quarter", "monitor")
CONFIDENCE = ("high", "medium", "low")

SECTOR_META = {
    "retail": ("Retail", "#F05587", "Grocery, FMCG, general merchandise, apparel, marketplaces, drinks (DRS), packaging (EPR), food and product labelling, product safety, Sunrise 2027 and digital product passports."),
    "construction": ("Construction", "#B78B20", "Construction products regulation, Building Safety Act and the golden thread, digital product records and passports, CCPI, PAS 2000, UKCA/CE marking and builders' merchants."),
    "healthcare": ("Healthcare", "#00B6DE", "MHRA medical device and IVD regulation (UDI, registration, post-market surveillance), medicines packaging and barcodes, NHS Scan4Safety, MDOR, NHS Supply Chain and eProcurement."),
}

ITEM_REQUIRED = {
    "url": str, "title": str, "summary": str, "what_changed": str, "why_it_matters_to_gs1": str,
    "sectors": list, "primary_sector": str, "impact": str, "relevance_score": int,
    "next_steps": list, "links": list,
}
ITEM_DEFAULTS = {
    "publisher": "", "issuing_body": "", "published_at": None, "change_type": "other", "jurisdiction": "UK",
    "gs1_standards_implicated": [], "affected_stakeholders": [], "key_dates": [], "confidence": "medium",
    "source_connector": "cursor-automation",
}
DIGEST_REQUIRED = {"window_start": str, "window_end": str, "headline": str, "executive_summary": str, "sector_overviews": list, "items": list}
DIGEST_DEFAULTS = {"status": "completed", "trigger": "automation", "cross_sector_themes": [], "stats": {}, "error": None, "is_sample": False}


class Problem(Exception):
    pass


def _iso(value: str, field: str) -> None:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Problem(f"{field}: {value!r} is not an ISO-8601 date/time") from exc


def validate_item(item: dict, idx: int) -> dict:
    where = f"items[{idx}]"
    for key, typ in ITEM_REQUIRED.items():
        if key not in item:
            raise Problem(f"{where}: missing required field {key!r}")
        if not isinstance(item[key], typ):
            raise Problem(f"{where}.{key}: expected {typ.__name__}")
    for key, default in ITEM_DEFAULTS.items():
        item.setdefault(key, json.loads(json.dumps(default)))
    if not re.match(r"^https?://", item["url"]):
        raise Problem(f"{where}.url must be an absolute http(s) URL")
    if not item["sectors"] or any(s not in SECTORS for s in item["sectors"]):
        raise Problem(f"{where}.sectors must be a non-empty subset of {SECTORS}")
    if item["primary_sector"] not in item["sectors"]:
        raise Problem(f"{where}.primary_sector must be one of its sectors")
    if item["impact"] not in IMPACTS:
        raise Problem(f"{where}.impact must be one of {IMPACTS}")
    if not 0 <= item["relevance_score"] <= 100:
        raise Problem(f"{where}.relevance_score must be 0-100")
    if item["change_type"] not in CHANGE_TYPES:
        raise Problem(f"{where}.change_type must be one of {CHANGE_TYPES}")
    if item["confidence"] not in CONFIDENCE:
        raise Problem(f"{where}.confidence must be one of {CONFIDENCE}")
    if item["published_at"]:
        _iso(item["published_at"], f"{where}.published_at")
    for j, link in enumerate(item["links"]):
        if not isinstance(link, dict) or not re.match(r"^https?://", link.get("url", "")) or not link.get("label"):
            raise Problem(f"{where}.links[{j}] needs url (http/https) and label")
        link.setdefault("kind", "other")
        if link["kind"] not in LINK_KINDS:
            raise Problem(f"{where}.links[{j}].kind must be one of {LINK_KINDS}")
    if not any(l["url"] == item["url"] for l in item["links"]):
        item["links"].insert(0, {"url": item["url"], "label": f"Source: {item['publisher'] or item['url']}", "kind": "primary"})
    for j, step in enumerate(item["next_steps"]):
        if not isinstance(step, dict) or not step.get("action"):
            raise Problem(f"{where}.next_steps[{j}] needs an action")
        step.setdefault("audience", "both")
        step.setdefault("priority", "next_quarter")
        if step["audience"] not in AUDIENCES or step["priority"] not in PRIORITIES:
            raise Problem(f"{where}.next_steps[{j}]: audience in {AUDIENCES}, priority in {PRIORITIES}")
    for j, kd in enumerate(item["key_dates"]):
        if not isinstance(kd, dict) or not kd.get("date") or not kd.get("label"):
            raise Problem(f"{where}.key_dates[{j}] needs date and label")
    return item


def validate_digest(path: Path) -> dict:
    digest = json.loads(path.read_text(encoding="utf-8"))
    digest_id = path.stem
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", digest_id):
        raise Problem(f"{path.name}: file name must be <YYYY-MM-DD>.json (window end date)")
    for key, typ in DIGEST_REQUIRED.items():
        if key not in digest or not isinstance(digest[key], typ):
            raise Problem(f"{path.name}: missing or invalid field {key!r}")
    for key, default in DIGEST_DEFAULTS.items():
        digest.setdefault(key, json.loads(json.dumps(default)))
    _iso(digest["window_start"], "window_start")
    _iso(digest["window_end"], "window_end")
    digest["id"] = digest_id
    digest.setdefault("created_at", digest["window_end"])
    digest.setdefault("completed_at", digest["window_end"])

    seen_sectors = set()
    for ov in digest["sector_overviews"]:
        if ov.get("sector") not in SECTORS:
            raise Problem(f"{path.name}: sector_overviews[].sector must be one of {SECTORS}")
        seen_sectors.add(ov["sector"])
        for k in ("headline", "summary"):
            if not isinstance(ov.get(k), str):
                raise Problem(f"{path.name}: sector_overviews[{ov['sector']}].{k} must be a string")
        ov.setdefault("top_priorities", [])
        ov.setdefault("watchlist", [])
    for s in SECTORS:
        if s not in seen_sectors:
            digest["sector_overviews"].append({"sector": s, "headline": "No relevant changes detected this week", "summary": "Nothing in this sector passed the GS1 UK relevance test this week.", "top_priorities": [], "watchlist": []})

    items = [validate_item(it, i) for i, it in enumerate(digest["items"])]
    items.sort(key=lambda i: i["relevance_score"], reverse=True)
    for n, it in enumerate(items, start=1):
        it["id"] = f"{digest_id}__{n}"
        it["digest_id"] = digest_id
    digest["items"] = items
    digest["item_count"] = len(items)
    digest["sector_counts"] = [
        {
            "sector": s,
            "total": sum(1 for i in items if s in i["sectors"] or i["primary_sector"] == s),
            "high": sum(1 for i in items if (s in i["sectors"] or i["primary_sector"] == s) and i["impact"] == "high"),
        }
        for s in SECTORS
    ]
    return digest


def summary_of(d: dict) -> dict:
    keys = ("id", "window_start", "window_end", "created_at", "completed_at", "status", "trigger", "headline", "is_sample", "item_count", "sector_counts")
    return {k: d[k] for k in keys}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate only; do not write index files")
    args = parser.parse_args()

    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(DIGEST_DIR.glob("*.json"))
    if not files:
        print("no digest files found in", DIGEST_DIR, file=sys.stderr)
        return 1

    digests: list[dict] = []
    ok = True
    for f in files:
        try:
            digests.append(validate_digest(f))
            print(f"OK   {f.name}: {len(digests[-1]['items'])} items")
        except (Problem, json.JSONDecodeError) as exc:
            ok = False
            print(f"FAIL {f.name}: {exc}", file=sys.stderr)
    if not ok:
        return 1
    if args.check:
        return 0

    digests.sort(key=lambda d: d["window_end"], reverse=True)
    for d in digests:
        (DIGEST_DIR / f"{d['id']}.json").write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    latest = next((d for d in digests if d["status"] == "completed"), digests[0])
    (DATA_DIR / "latest.json").write_text(json.dumps(latest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    index = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": {
            "app": "GS1 UK Regulatory Radar",
            "environment": "static",
            "llm_provider": "cursor-automation",
            "llm_configured": True,
            "web_search_provider": "cursor-agent",
            "schedule": "mon 08:00 (Europe/London)",
            "timezone": "Europe/London",
            "next_run": None,
            "running": False,
            "latest_digest_id": latest["id"],
            "sectors": [{"id": s, "name": n, "colour": c, "description": desc} for s, (n, c, desc) in SECTOR_META.items()],
        },
        "digests": [summary_of(d) for d in digests],
    }
    (DATA_DIR / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote index.json ({len(digests)} digests) and latest.json ({latest['id']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
