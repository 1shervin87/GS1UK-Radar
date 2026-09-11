# Digest JSON schema

File: `frontend/public/data/digests/<YYYY-MM-DD>.json` (date = end of the monitoring window).
`automation/build_index.py` validates it, sorts items by relevance, assigns `id`/`digest_id`,
computes `item_count` and `sector_counts`, and regenerates `index.json` and `latest.json`.
Fields marked *generated* must not be written by hand.

```jsonc
{
  "window_start": "2026-09-07T08:00:00+01:00",   // ISO-8601, required
  "window_end":   "2026-09-14T08:00:00+01:00",   // ISO-8601, required
  "status": "completed",                         // default "completed"
  "trigger": "automation",                       // default
  "is_sample": false,                            // default
  "headline": "One-line headline for the week",
  "executive_summary": "4–6 sentences on what this week means for GS1 UK.",
  "cross_sector_themes": ["...", "..."],
  "sector_overviews": [                          // one entry per sector; missing sectors get a default "nothing this week"
    {
      "sector": "retail",                        // retail | construction | healthcare
      "headline": "...",
      "summary": "3–5 sentences.",
      "top_priorities": ["<item title>", "..."],
      "watchlist": ["...", "..."]
    }
  ],
  "stats": { "queries": 55, "pages_reviewed": 140, "items_kept": 7 },   // free-form numbers
  "items": [
    {
      "url": "https://www.gov.uk/...",           // primary source, absolute URL, required
      "title": "Specific headline (<=110 chars)",
      "publisher": "gov.uk",
      "issuing_body": "MHRA",
      "published_at": "2026-09-10T00:00:00+01:00", // ISO-8601 or null
      "change_type": "consultation",             // legislation | draft_legislation | consultation | guidance | policy | enforcement | standard | industry_scheme | eu_international | nhs_programme | other
      "jurisdiction": "UK",                      // UK | GB | England | Scotland | Wales | Northern Ireland | EU (affects UK) | International (affects UK)
      "sectors": ["healthcare"],                 // non-empty subset of retail | construction | healthcare
      "primary_sector": "healthcare",            // must be in sectors
      "impact": "high",                          // high | medium | low
      "relevance_score": 92,                     // 0–100; publish only >= 55
      "summary": "2–3 sentences.",
      "what_changed": "Factual paragraph(s).",
      "why_it_matters_to_gs1": "Analytical paragraph(s).",
      "gs1_standards_implicated": ["GTIN", "GS1 DataMatrix"],
      "affected_stakeholders": ["Medical device manufacturers", "NHS trusts"],
      "key_dates": [ { "date": "2026-12-01", "label": "Regulations expected to be adopted" } ],
      "next_steps": [
        { "audience": "gs1_uk",  "action": "...", "priority": "now" },          // audience: gs1_uk | members | both; priority: now | next_quarter | monitor
        { "audience": "members", "action": "...", "priority": "next_quarter" }
      ],
      "links": [
        { "url": "https://...", "label": "GOV.UK: ...", "kind": "primary" }     // kind: primary | official | guidance | gs1 | news | other
      ],
      "confidence": "high"                       // high | medium | low
      // "id", "digest_id" – generated
    }
  ]
  // "id", "item_count", "sector_counts", "created_at", "completed_at" – generated
}
```

Multi-paragraph text: separate paragraphs with a blank line (`\n\n`).
