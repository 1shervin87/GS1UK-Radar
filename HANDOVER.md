# Handover for a Cursor cloud agent with repository access

You are setting up the **GS1 UK Regulatory Radar** in this (currently empty) repository. The
complete, tested source code was produced by a previous agent that had no repository access.

## Step 1 – obtain the source

Try to download the bundle (it may have expired; if so go to the fallback):

```bash
curl -fL -o /tmp/radar.tar.gz "https://d.uguu.se/hJFBPpPm.tar.gz" && tar -xzf /tmp/radar.tar.gz -C /tmp
# expected md5: 600ef6306a0bb34d6bdad61387c6993b
cp -r /tmp/gs1uk-regulatory-radar/. .
```

**Fallback (bundle unavailable):** rebuild the project from the specification in section 4 of this
file. Keep the same file layout and behaviour.

## Step 2 – verify locally

```bash
cd frontend && npm ci && VITE_DATA_MODE=static npm run build && cd ..
python3 automation/build_index.py --check
```

## Step 3 – publish

1. Commit everything to `main` and push.
2. The workflow `.github/workflows/pages.yml` deploys the static site to GitHub Pages. It tries to enable
   Pages automatically (`enablement: true`). If the deploy job fails with a Pages-not-enabled error, tell
   the user to open *Settings → Pages → Source: GitHub Actions* once, then re-run the workflow.
3. Report the site URL (`https://<owner>.github.io/<repo>/`) to the user.

## Step 4 – tell the user how to switch on the weekly automation

The agent cannot create Cursor Automations itself. Give the user these two options:

- In Cursor, type `/automate` and say: *"Every Monday at 08:00 Europe/London, on repository <repo>, follow
  the instructions in automation/PROMPT.md and push the result to main."*
- Or at cursor.com/automations: Scheduled trigger, cron `0 8 * * 1`, timezone Europe/London, repository
  `<repo>`, prompt = contents of `automation/PROMPT.md` below the horizontal rule.

Suggest running the automation once manually so the first real digest replaces the sample.

---

## 4. Specification (for the rebuild fallback)

**Purpose.** Weekly digest of UK regulatory / legislative / policy / industry-scheme changes relevant to
GS1 UK across three sectors (retail, construction, healthcare), each item explained (what changed, why it
matters to GS1 UK, GS1 standards implicated, stakeholders, key dates, recommended next steps for GS1 UK
and for members, source links). Website: Overview page + three sector tabs + item detail + archive/search.

**GS1 UK reference brief** (`backend/app/knowledge/gs1_context.md`, injected into every AI prompt):
GS1 UK *is* the UK member organisation of GS1 – neutral, not-for-profit, member-owned standards body,
~60,000 UK members; only authorised UK licensor of GS1 Company Prefixes → GTIN, GLN, SSCC, GSRN, GIAI,
GMN etc.; owner of data carriers (EAN/UPC, GS1-128, GS1 DataMatrix, GS1 QR / GS1 Digital Link = "QR codes
powered by GS1") and data-sharing standards (GDSN/productDNA, EPCIS 2.0, EDI); UK programmes: Sunrise 2027,
DRS readiness (Exchange for Change, go-live 1 Oct 2027, barcodes must be re-registered), NHS Scan4Safety /
MDOR / NHS Supply Chain IMS, construction golden thread / Construction Products Reform White Paper (25 Feb
2026) / General Safety Requirement consultation, EU DPP/ESPR, EUDR (30 Dec 2026), UK e-invoicing (1 Apr
2029), MHRA draft Medical Devices (Amendment) Regulations 2026 making UDI compulsory (adoption Dec 2026,
in force Jun 2027). GS1 UK *is not*: a regulator, government body, certification/conformity body,
compliance guarantee, barcode printer, or BSI Identify/UKCA/CE. Relevance test (8 points): requires or
references unique identification; machine-readable data carriers; structured product data / digital
records / registries; on-pack labelling changes; traceability / recall / market-surveillance duties;
identifier-keyed registries; planning timelines; NHS/MHRA/OPSS/MHCLG/Defra/DBT/HMRC/Exchange for Change
acting on data or barcoding. Score 0–100, publish ≥ 55. British English; never claim GS1 standards are
legally mandated unless the source says so.

**Static data contract** – see `automation/DIGEST_SCHEMA.md` (digest: window_start, window_end, headline,
executive_summary, cross_sector_themes[], sector_overviews[{sector, headline, summary, top_priorities[],
watchlist[]}], stats{}, items[{url, title, publisher, issuing_body, published_at, change_type,
jurisdiction, sectors[], primary_sector, impact high|medium|low, relevance_score, summary, what_changed,
why_it_matters_to_gs1, gs1_standards_implicated[], affected_stakeholders[], key_dates[{date,label}],
next_steps[{audience gs1_uk|members|both, action, priority now|next_quarter|monitor}],
links[{url,label,kind}], confidence}]). `automation/build_index.py` (stdlib) validates, sorts by
relevance, sets item ids `<digestId>__<n>`, computes item_count/sector_counts, writes
`frontend/public/data/index.json` (status + digest summaries) and `latest.json`.

**Frontend** – Vite + React 19 + TypeScript + Tailwind v4 + react-router + lucide-react. GS1 palette:
Blue #002C6C, Orange #F26334, link #008DBD, greys #454545/#888B8D/#B1B3B3/#F4F4F4; sectors Retail
Raspberry #F05587, Construction Honey #B78B20, Healthcare Sky #00B6DE; font Montserrat (Gotham stand-in).
Routes: `/` overview (hero with headline/executive summary/counts, three sector cards, cross-sector
themes, top items), `/retail|/construction|/healthcare` (sector overview, priorities, watchlist,
filter/sort item list), `/items/:id`, `/archive` (search + digest table). Header: logo "GS1 UK |
Regulatory Radar", tabs, week selector, sample-data banner. `VITE_DATA_MODE=static` reads JSON from
`<BASE_URL>/data/…`; `VITE_BASE=/<repo>/`; router basename from `import.meta.env.BASE_URL`; copy
`index.html` to `404.html` for deep links.

**Automation** – `automation/PROMPT.md`: the weekly Cursor Automation prompt (read brief + query bank,
search GOV.UK / legislation.gov.uk / regulators / gs1uk.org / trade press for the past 7 days, judge
relevance sceptically, analyse, write `frontend/public/data/digests/<YYYY-MM-DD>.json`, run
`build_index.py`, commit `digest: week to <date>` to main).

**Optional Python backend** (`backend/`, FastAPI + APScheduler cron Mon 08:00 Europe/London + SQLAlchemy;
connectors GOV.UK Search API, legislation.gov.uk daily feeds, Tavily/DuckDuckGo; LLM Anthropic/OpenAI/
OpenAI-compatible base URL e.g. Gemini free tier) serves the same UI at `/` with a REST API – only needed
if the user later wants a self-hosted server instead of Cursor Automations.

**Sample digest** – include one `is_sample: true` digest (window 4–11 Sep 2026) with real sourced items:
DRS one-year countdown (gs1uk.org, 9 Sep 2026), EU DPP Registry live (13 Aug 2026), EUDR (30 Dec 2026),
MHCLG GSR consultation + White Paper (25 Feb 2026), MHRA draft UDI regulations (8 May 2026), NHS
Scan4Safety/New Hospitals Programme 2027, UK e-invoicing 2029.
