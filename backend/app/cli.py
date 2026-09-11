"""Command line helpers.

    python -m app.cli run-now            # run the full search + analysis pipeline immediately
    python -m app.cli seed-demo          # load a sample digest so the UI can be explored without API keys
    python -m app.cli show-queries       # print the search query bank
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from .analysis.pipeline import run_weekly_digest
from .config import get_settings
from .db import init_db
from .knowledge.sectors import all_queries


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(prog="radar")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run-now", help="Run the weekly pipeline now")
    run.add_argument("--lookback-days", type=int, default=None)
    sub.add_parser("seed-demo", help="Insert the sample digest")
    sub.add_parser("show-queries", help="Print the query bank")
    exp = sub.add_parser("export-static", help="Export a digest as static JSON for the GitHub Pages site")
    exp.add_argument("--digest-id", type=int, default=None, help="defaults to the latest completed digest")
    exp.add_argument("--out-dir", default="../frontend/public/data/digests")
    args = parser.parse_args()

    init_db()
    settings = get_settings()

    if args.cmd == "run-now":
        if args.lookback_days:
            settings = settings.model_copy(update={"lookback_days": args.lookback_days})
        digest_id = asyncio.run(run_weekly_digest(settings, trigger="manual"))
        print(f"digest {digest_id} completed")
    elif args.cmd == "seed-demo":
        from .seed_demo import seed

        print(f"seeded sample digest {seed()}")
    elif args.cmd == "show-queries":
        for sector, q in all_queries():
            print(f"[{sector or 'cross-sector':12}] {q}")
    elif args.cmd == "export-static":
        print(export_static(args.digest_id, args.out_dir))


def export_static(digest_id: int | None, out_dir: str) -> str:
    """Write a digest as <window_end date>.json in the schema used by automation/build_index.py."""
    import json
    from pathlib import Path

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from .db import Digest, session_scope

    item_fields = (
        "url", "title", "publisher", "issuing_body", "published_at", "change_type", "jurisdiction", "sectors",
        "primary_sector", "impact", "relevance_score", "summary", "what_changed", "why_it_matters_to_gs1",
        "gs1_standards_implicated", "affected_stakeholders", "key_dates", "next_steps", "links", "confidence",
        "source_connector",
    )
    with session_scope() as s:
        stmt = select(Digest).options(selectinload(Digest.items))
        stmt = stmt.where(Digest.id == digest_id) if digest_id else stmt.where(Digest.status == "completed").order_by(Digest.window_end.desc())
        digest = s.execute(stmt).scalars().first()
        if not digest:
            raise SystemExit("no digest found")
        payload = {
            "window_start": digest.window_start.isoformat(),
            "window_end": digest.window_end.isoformat(),
            "status": digest.status,
            "trigger": digest.trigger,
            "is_sample": digest.is_sample,
            "headline": digest.headline,
            "executive_summary": digest.executive_summary,
            "cross_sector_themes": digest.cross_sector_themes,
            "sector_overviews": digest.sector_overviews,
            "stats": digest.stats,
            "items": [
                {f: (getattr(i, f).isoformat() if f == "published_at" and getattr(i, f) else getattr(i, f)) for f in item_fields}
                for i in digest.items
            ],
        }
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"{digest.window_end.date().isoformat()}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return str(path)


if __name__ == "__main__":
    main()
