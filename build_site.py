"""Build site/index.html from data/filings.json. Static, no JS, fast to index."""
import json
from datetime import datetime, timezone
from pathlib import Path
from html import escape

ROOT = Path(__file__).parent
filings = json.loads((ROOT / "data" / "filings.json").read_text()) if (ROOT / "data" / "filings.json").exists() else {}
active = [v for v in filings.values() if v.get("active")]
venues = sorted([v for v in active if v["is_new_venue"]], key=lambda v: v.get("first_seen", ""), reverse=True)
transfers = sorted([v for v in active if not v["is_new_venue"] and v["category"] not in ("beer_wine_store", "liquor_store", "other")], key=lambda v: v["name"])
retail = sorted([v for v in active if v["category"] in ("beer_wine_store", "liquor_store")], key=lambda v: v["name"])
updated = datetime.now(timezone.utc).strftime("%B %d, %Y")

LABEL = {"restaurant": "Restaurant", "bar": "Bar", "beer_wine_bar": "Beer & wine bar", "hotel": "Hotel",
         "private_club": "Private club", "microbrewery": "Brewery", "tasting_room": "Tasting room",
         "beer_wine_store": "Beer & wine retail", "liquor_store": "Liquor store", "other": "Other"}


def row(v):
    pdf = f' · <a href="{escape(v["pdf_application"])}">application</a>' if v.get("pdf_application") else ""
    return (f'<li><strong>{escape(v["name"])}</strong> <span class="tag">{LABEL.get(v["category"], v["category"])}</span><br>'
            f'{escape(v["address"])}, Phoenix · District {v["district"]} · {escape(v["type"])}'
            f' · comment period ends {escape(v["comment_deadline"].replace(" 5:00 PM", ""))}{pdf}</li>')


html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>New Restaurants &amp; Bars Opening Soon in Phoenix, AZ ({datetime.now().year}) — Liquor License Tracker</title>
<meta name="description" content="Every new restaurant, bar and brewery that just filed for a liquor license in Phoenix, updated daily from City of Phoenix public records. {len(venues)} new venues pending right now.">
<style>
:root{{--bg:#fff;--fg:#1a1a1a;--muted:#666;--line:#e5e5e5;--tag:#f1f1f1}}
@media(prefers-color-scheme:dark){{:root{{--bg:#111;--fg:#eee;--muted:#aaa;--line:#333;--tag:#222}}}}
body{{font:16px/1.5 system-ui,sans-serif;max-width:760px;margin:0 auto;padding:24px 16px;background:var(--bg);color:var(--fg)}}
h1{{font-size:1.6rem;line-height:1.2}} h2{{margin-top:2.2rem;font-size:1.2rem;border-bottom:1px solid var(--line);padding-bottom:.3rem}}
ul{{list-style:none;padding:0}} li{{padding:.7rem 0;border-bottom:1px solid var(--line)}}
.tag{{font-size:.75rem;background:var(--tag);padding:2px 8px;border-radius:99px;margin-left:6px}}
.muted{{color:var(--muted);font-size:.9rem}} a{{color:inherit}}
.cta{{border:1px solid var(--line);padding:14px;border-radius:8px;margin:1.5rem 0}}
</style></head><body>
<h1>New restaurants &amp; bars opening soon in Phoenix</h1>
<p class="muted">Sourced daily from City of Phoenix liquor license filings. A "New" application usually means a venue 1–6 months from opening. Updated {updated}. Not affiliated with the City of Phoenix.</p>
<div class="cta"><strong>Sell to restaurants and bars?</strong> Get every new filing in your inbox each week, with applicant details and address, before they open. <a href="#subscribe">Weekly alert for vendors →</a></div>
<h2>{len(venues)} new venues pending</h2><ul>{''.join(row(v) for v in venues) or '<li class="muted">None currently listed.</li>'}</ul>
<h2>Ownership changes at existing venues ({len(transfers)})</h2><ul>{''.join(row(v) for v in transfers)}</ul>
<h2>Retail beer, wine &amp; liquor ({len(retail)})</h2><ul>{''.join(row(v) for v in retail)}</ul>
<h2 id="subscribe">Weekly vendor alert</h2>
<p>Coming soon. For now, the raw data is at <a href="data/new.json">data/new.json</a> and <a href="data/filings.json">data/filings.json</a>.</p>
<p class="muted">Source: <a href="https://www.phoenix.gov/administration/departments/cityclerk/programs-services/license-services/new-applications.html">City of Phoenix, Newly Received Liquor License Applications</a>. Public record under A.R.S. 4-201.</p>
</body></html>"""
(ROOT / "site").mkdir(exist_ok=True)
(ROOT / "site" / "index.html").write_text(html)
print(f"site built: {len(venues)} new venues, {len(transfers)} transfers, {len(retail)} retail")
