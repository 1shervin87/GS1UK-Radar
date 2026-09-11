# GS1 UK Regulatory Radar

A weekly, AI-analysed digest of UK regulatory, legislative, policy and major industry-scheme
changes that matter to **GS1 UK** and its members across **Retail**, **Construction** and
**Healthcare**.

Every **Monday at 08:00 (Europe/London)** the service:

1. Searches broadly for the previous seven days – GOV.UK Search API, legislation.gov.uk new-legislation
   feeds, and general web/news search (Tavily or DuckDuckGo) – using a 55-query bank that covers each sector
   plus cross-sector identification/traceability topics.
2. De-duplicates and fetches the underlying pages.
3. Runs an AI agent (Anthropic Claude or OpenAI) grounded in a **GS1 UK reference brief** to triage
   relevance, then produces for each kept item: what changed, *why it matters to GS1 UK*, the GS1
   standards implicated, affected stakeholders, key dates, recommended next steps (for GS1 UK and for
   members) and source links.
4. Writes an executive overview plus a per-sector overview, and publishes everything to the website.

The site has an **Overview** page (all three sectors) and dedicated **Retail / Construction /
Healthcare** tabs, plus item detail pages, a searchable archive of previous weeks and a
"Run now" admin action. Styling follows the GS1 global brand palette (GS1 Blue `#002C6C`,
GS1 Orange `#F26334`; sector colours Raspberry / Honey / Sky).

---

## What GS1 UK is – and is not (the lens the AI uses)

The file `backend/app/knowledge/gs1_context.md` is injected into every prompt. In short:

- **Is**: the UK member organisation of GS1, a neutral not-for-profit standards body; the only
  authorised UK issuer of GS1 Company Prefixes and therefore GTINs, GLNs, SSCCs, GSRNs, GIAIs;
  owner of barcode/2D standards (EAN/UPC, GS1 DataMatrix, GS1 Digital Link / "QR codes powered by GS1"),
  data-sharing standards (GDSN/productDNA, EPCIS, EDI) and UK programmes (Sunrise 2027, DRS readiness,
  NHS Scan4Safety, construction golden thread / DPP readiness).
- **Is not**: a regulator, government body, certification/conformity body, compliance guarantee,
  or a label/barcode printer. Regulators (MHRA, MHCLG/BSR, OPSS, Defra, DBT, HMRC…) decide *what* must
  be identified, labelled, traced and reported; GS1 standards define *how* to do that interoperably.

A change is flagged as relevant when it requires or references unique identification, machine-readable
data carriers, structured product-data sharing or digital records, changes on-pack labelling, or alters
traceability/recall/market-surveillance duties in one of the three sectors.

---

## Two ways to run it

| | **A. Cursor Automation + GitHub Pages** (recommended, no API keys, no server) | **B. Self-hosted Python service** |
| --- | --- | --- |
| Who does the AI analysis | A scheduled **Cursor cloud agent** (your existing Cursor plan) | Anthropic / OpenAI / Gemini API (needs a key) |
| Where the site lives | GitHub Pages (free, static) | Any host running Docker / uvicorn |
| Weekly trigger | Cursor Automation cron `0 8 * * 1` Europe/London | Built-in APScheduler (Mon 08:00 Europe/London) |
| Setup files | `automation/PROMPT.md`, `.github/workflows/pages.yml` | `Dockerfile`, `docker-compose.yml`, `.env.example` |

### A. Set up with Cursor Automations (step by step)

1. **Create a GitHub repository** (e.g. `gs1uk-regulatory-radar`) and push this code to `main`.
2. **Enable GitHub Pages**: repo *Settings → Pages → Source: GitHub Actions*. The workflow
   `.github/workflows/pages.yml` builds the static site (`VITE_DATA_MODE=static`) on every push and
   publishes it at `https://<owner>.github.io/<repo>/`. The sample digest already in
   `frontend/public/data/` appears immediately.
3. **Connect the repo to Cursor** (cursor.com → Integrations → GitHub) if not already connected.
4. **Create the automation** at [cursor.com/automations](https://cursor.com/automations):
   - Trigger: *Scheduled* → cron `0 8 * * 1`, timezone Europe/London.
   - Repository: your new repo, branch `main`.
   - Prompt: paste the contents of `automation/PROMPT.md` (below the horizontal rule).
   - Tools: default agent tools; optionally *Send to Slack*.
   - Save and activate. (You can also open the repo in a Cursor agent and type `/automate` describing the above.)
5. Each Monday the agent researches the week, writes `frontend/public/data/digests/<date>.json`,
   runs `python automation/build_index.py` (validates + regenerates `index.json`/`latest.json`) and
   pushes. GitHub Pages redeploys within a minute or two.

To test the whole loop right away, run the automation manually once from cursor.com/automations,
or start a cloud agent on the repo with the prompt "Follow automation/PROMPT.md and produce this week's digest".

Add digest data manually? Drop a file matching `automation/DIGEST_SCHEMA.md` into
`frontend/public/data/digests/` and run `python automation/build_index.py`.

### B. Self-hosted Python service

Follow *Quick start* below. If you have no paid LLM account, Google Gemini's free tier works via its
OpenAI-compatible endpoint (see `.env.example`: `LLM_PROVIDER=openai`, `OPENAI_BASE_URL=…`,
`OPENAI_MODEL=gemini-2.5-flash`).

---

## Quick start (local, option B)

Requirements: Python 3.12+, Node 22+.

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env          # then add ANTHROPIC_API_KEY (or OPENAI_API_KEY) and ADMIN_TOKEN
python -m app.cli seed-demo      # optional: sample digest so the UI has content
uvicorn app.main:app --reload --port 8000

# 2. Frontend (dev server with API proxy)
cd ../frontend
npm install
npm run dev                      # http://localhost:5173
```

Production build: `cd frontend && npm run build` writes to `backend/static/`, which FastAPI serves
with SPA fallback, so a single `uvicorn` process serves both API and UI.

### Docker

```bash
cp .env.example .env   # fill in keys
docker compose up -d --build
# http://localhost:8000
```

The SQLite database lives in the `radar-data` volume. Set `DATABASE_URL` to a PostgreSQL URL to use
Postgres instead (SQLAlchemy; install `psycopg[binary]`).

---

## Configuration

All settings are environment variables (see `.env.example`).

| Variable | Default | Purpose |
| --- | --- | --- |
| `LLM_PROVIDER` | `anthropic` | `anthropic` or `openai` |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | – | Required for live runs |
| `ANTHROPIC_MODEL` / `OPENAI_MODEL` | `claude-sonnet-4-20250514` / `gpt-4o` | Model names |
| `TAVILY_API_KEY` | – | Optional; better dated news search. Falls back to DuckDuckGo |
| `SCHEDULE_*` | Mon 08:00 Europe/London | Cron schedule; `SCHEDULE_ENABLED=false` to disable |
| `LOOKBACK_DAYS` | 7 | Search window |
| `RUN_ON_STARTUP` | false | Run a digest when the server starts |
| `LLM_MAX_ITEMS_TO_ANALYSE` | 40 | Cap on deep analyses per run (cost control) |
| `RELEVANCE_THRESHOLD` | 55 | Minimum AI relevance score (0–100) to publish |
| `ADMIN_TOKEN` | – | Bearer token for `POST /api/admin/run` ("Run now") |
| `DATABASE_URL` | `sqlite:///./data/radar.db` | SQLAlchemy URL |

---

## Running the pipeline manually

```bash
cd backend
python -m app.cli run-now                 # full run for the last 7 days
python -m app.cli run-now --lookback-days 14
python -m app.cli show-queries            # print the query bank
```

Or from the UI: **Run now** (prompts for `ADMIN_TOKEN`). Or `curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8000/api/admin/run`.

---

## API

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/status` | Schedule, next run, provider, sectors |
| GET | `/api/digests` | List weekly digests (newest first) |
| GET | `/api/digests/latest` | Latest completed digest with items and overviews |
| GET | `/api/digests/{id}` | Specific digest |
| GET | `/api/digests/{id}/items?sector=retail&impact=high` | Filtered items |
| GET | `/api/items/{id}` | Full item analysis |
| GET | `/api/items?q=UDI&sector=healthcare` | Search across all digests |
| GET | `/api/runs` | Run log |
| POST | `/api/admin/run` | Trigger a run (Bearer `ADMIN_TOKEN`) |

Interactive docs at `/docs`.

---

## Project layout

```
backend/
  app/
    main.py              FastAPI app, static SPA serving, lifespan (scheduler)
    config.py            Settings (env vars)
    db.py                SQLAlchemy models: Digest, Item, RunLog
    scheduler.py         APScheduler cron (Monday 08:00 Europe/London), manual trigger
    cli.py               run-now / seed-demo / show-queries
    seed_demo.py         Sample digest built from real, sourced developments
    knowledge/
      gs1_context.md     What GS1 UK is / is not; relevance test; sector definitions
      sectors.py         Sector metadata, colours, 55-query search bank, keyword heuristics
    connectors/
      govuk.py           GOV.UK Search API (no key)
      legislation.py     legislation.gov.uk daily new-legislation Atom feeds (no key)
      websearch.py       Tavily (key) or DuckDuckGo (no key)
      fetcher.py         Page fetch + trafilatura text extraction
    analysis/
      llm.py             Provider-agnostic JSON completion (Anthropic / OpenAI)
      prompts.py         Triage, per-item analysis and weekly overview prompts
      schemas.py         Pydantic schemas for structured AI output
      pipeline.py        Orchestration: search → fetch → triage → analyse → overview → persist
    api/
      routes.py          REST endpoints
frontend/                Vite + React 19 + TypeScript + Tailwind v4
  src/api.ts             REST client + static-JSON adapter (VITE_DATA_MODE=static)
  src/pages/             Overview, SectorPage (retail/construction/healthcare), ItemPage, Archive
  src/components/        Layout (header, tabs, week picker, Run now), UI primitives
  public/data/           Static digests (written by the Cursor Automation): digests/<date>.json, index.json, latest.json
automation/
  PROMPT.md              The weekly Cursor Automation prompt
  DIGEST_SCHEMA.md       JSON contract for a weekly digest
  build_index.py         Validates digests, regenerates index.json / latest.json (stdlib only)
.github/workflows/pages.yml   Builds the static site and deploys to GitHub Pages
Dockerfile, docker-compose.yml, .env.example
```

---

## Extending

- **Add a sector or query**: edit `backend/app/knowledge/sectors.py` (queries, keywords, colour) and
  `frontend/src/api.ts` (`SECTOR_META`). The relevance brief in `gs1_context.md` should describe the
  new sector's regulators and GS1 touchpoints.
- **Add a source**: implement a connector returning `Candidate` objects and register it in
  `connectors/__init__.py::collect_candidates`.
- **Notifications**: `pipeline.run_weekly_digest` returns the digest id on completion – a good hook for
  Teams/Slack/email posting.

## Notes

- AI output is decision support, not legal advice. Every item links to its primary source.
- Sample data (`seed-demo`) is flagged `is_sample` and labelled in the UI; the first real run becomes "latest".
- Gotham (GS1's brand typeface) is licensed; the UI uses Montserrat as a free equivalent with
  Verdana/system fallbacks per the GS1 brand manual.
