# PHX Opening Soon — Phoenix liquor-license filing tracker

**Read `data/run_log.jsonl` first every session.** One line per daily run: live count, new count, errors.
If `errors` is non-empty or `live` drops to 0, the city changed the page; fix `parse_district()` in `scrape.py`.

## What it does
Daily GitHub Action → pulls 8 council-district HTML fragments from phoenix.gov → parses every pending
liquor-license application → diffs against `data/filings.json` → writes `data/new.json` → rebuilds
`site/index.html` → deploys to GitHub Pages.

## Product layers (in build order)
1. **Public page** (`site/`) — SEO magnet: "new restaurants opening Phoenix". Live via GitHub Pages. ✅
2. **Weekly vendor alert** — paid, $25–50/mo. Send `data/new.json` filtered to `is_new_venue` via Resend/Beehiiv. ⬜
3. **Consumer newsletter** — free, sponsor-funded. ⬜
4. **Second metro** — Scottsdale ✅ (council agenda PDFs, `scottsdale.py`) · Mesa ✅ (Legistar API, `mesa.py`). Tempe / Gilbert / Chandler ⬜ (not on Legistar; need their own parsers)

## Data fields
name, address, district, series (AZ DLLC series number), series_label, type (New | Acquisition of Control |
Person/Location Transfer...), comment_deadline, category, is_new_venue, app_id, pdf_application (state
application PDF — has applicant name + contact), first_seen, last_seen, active.

## Run locally
    pip install -r requirements.txt && python scrape.py && python build_site.py

## Decisions log
- 2026-09-18: Added Mesa via Legistar web API (no auth, JSON, includes agent name). Tempe/Chandler/Gilbert return HTTP 500 on Legistar → different systems.
- 2026-09-18: Added Scottsdale. No standing list there; items appear on Council agenda PDFs ~10 days before meeting. Parsed agendas tracked in data/scottsdale_agendas.json; records stay active 45 days past meeting date.
- 2026-09-17: Source confirmed. 8 static endpoints, no auth, ~58 live filings. Chose GitHub Actions + Pages
  (free, zero servers). Alert email deferred until domain + sender are set up.
# PHX Opening Soon — Phoenix liquor-license filing tracker

**Read `data/run_log.jsonl` first every session.** One line per daily run: live count, new count, errors.
If `errors` is non-empty or `live` drops to 0, the city changed the page; fix `parse_district()` in `scrape.py`.

## What it does
Daily GitHub Action → pulls 8 council-district HTML fragments from phoenix.gov → parses every pending
liquor-license application → diffs against `data/filings.json` → writes `data/new.json` → rebuilds
`site/index.html` → deploys to GitHub Pages.

## Product layers (in build order)
1. **Public page** (`site/`) — SEO magnet: "new restaurants opening Phoenix". Live via GitHub Pages. ✅
2. **Weekly vendor alert** — paid, $25–50/mo. Send `data/new.json` filtered to `is_new_venue` via Resend/Beehiiv. ⬜
3. **Consumer newsletter** — free, sponsor-funded. ⬜
4. **Second metro** — Scottsdale ✅ (council agenda PDFs, `scottsdale.py`). Tempe / Mesa / Gilbert / Chandler ⬜

## Data fields
name, address, district, series (AZ DLLC series number), series_label, type (New | Acquisition of Control |
Person/Location Transfer...), comment_deadline, category, is_new_venue, app_id, pdf_application (state
application PDF — has applicant name + contact), first_seen, last_seen, active.

## Run locally
    pip install -r requirements.txt && python scrape.py && python build_site.py

## Decisions log
- 2026-09-18: Added Scottsdale. No standing list there; items appear on Council agenda PDFs ~10 days before meeting. Parsed agendas tracked in data/scottsdale_agendas.json; records stay active 45 days past meeting date.
- 2026-09-17: Source confirmed. 8 static endpoints, no auth, ~58 live filings. Chose GitHub Actions + Pages
  (free, zero servers). Alert email deferred until domain + sender are set up.
