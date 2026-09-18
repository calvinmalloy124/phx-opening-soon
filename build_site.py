"""Build site/index.html from data/filings.json. Static, no JS, fast to index."""
import json
from datetime import datetime, timezone
from pathlib import Path
from html import escape

ROOT = Path(__file__).parent
filings = json.loads((ROOT / "data" / "filings.json").read_text()) if (ROOT / "data" / "filings.json").exists() else {}
active = [v for v in filings.values() if v.get("active")]
CITIES = ["Phoenix", "Scottsdale", "Mesa"]
venues = sorted([v for v in active if v["is_new_venue"]], key=lambda v: v.get("first_seen", ""), reverse=True)
transfers = sorted([v for v in active if not v["is_new_venue"] and v["category"] not in ("beer_wine_store", "liquor_store", "other")], key=lambda v: v["name"])
retail = sorted([v for v in active if v["category"] in ("beer_wine_store", "liquor_store")], key=lambda v: v["name"])
updated = datetime.now(timezone.utc).strftime("%B %d, %Y")

LABEL = {"restaurant": "Restaurant", "bar": "Bar", "beer_wine_bar": "Beer & wine bar", "hotel": "Hotel",
         "private_club": "Private club", "microbrewery": "Brewery", "tasting_room": "Tasting room",
         "beer_wine_store": "Beer & wine retail", "liquor_store": "Liquor store", "other": "Other"}


def row(v):
    lbl = "application" if v.get("city") == "Phoenix" else ("council file" if v.get("city") == "Mesa" else "council agenda")
    pdf = f' · <a href="{escape(v["pdf_application"])}">{lbl}</a>' if v.get("pdf_application") else ""
    where = f'{escape(v["address"])}, {escape(v.get("city", "Phoenix"))}'
    if v.get("district"):
        where += f' · District {v["district"]}'
    when = escape(v["comment_deadline"].replace(" 5:00 PM", ""))
    when = ("comment period ends " + when) if v.get("city") == "Phoenix" else when
    return (f'<li><strong>{escape(v["name"])}</strong> <span class="tag">{LABEL.get(v["category"], v["category"])}</span>'
            f'<span class="tag">{escape(v.get("city", "Phoenix"))}</span><br>{where} · {escape(v["type"])} · {when}{pdf}</li>')


html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>New Restaurants &amp; Bars Opening Soon in Phoenix, Scottsdale &amp; Mesa, AZ ({datetime.now().year}) — Liquor License Tracker</title>
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
<h1>New restaurants &amp; bars opening soon in Phoenix, Scottsdale &amp; Mesa</h1>
<p class="muted">Sourced daily from City of Phoenix liquor license filings, Scottsdale City Council agendas and Mesa City Council filings. A "New" application usually means a venue 1–6 months from opening. Updated {updated}. Not affiliated with the City of Phoenix.</p>
<div class="cta"><strong>Sell to restaurants and bars?</strong> Get every new filing in your inbox each week, with applicant details and address, before they open. <a href="#subscribe">Weekly alert for vendors →</a></div>
<h2>{len(venues)} new venues pending</h2><ul>{''.join(row(v) for v in venues) or '<li class="muted">None currently listed.</li>'}</ul>
<p class="muted">By city: {' · '.join(f"{c} {sum(1 for v in venues if v.get('city')==c)}" for c in CITIES)}</p>
<h2>Ownership changes at existing venues ({len(transfers)})</h2><ul>{''.join(row(v) for v in transfers)}</ul>
<h2>Retail beer, wine &amp; liquor ({len(retail)})</h2><ul>{''.join(row(v) for v in retail)}</ul>
<h2 id="subscribe">Weekly vendor alert</h2>
<p>Coming soon. For now, the raw data is at <a href="data/new.json">data/new.json</a> and <a href="data/filings.json">data/filings.json</a>.</p>
<p class="muted">Sources: <a href="https://www.phoenix.gov/administration/departments/cityclerk/programs-services/license-services/new-applications.html">City of Phoenix, Newly Received Liquor License Applications</a> · <a href="https://ww2.scottsdaleaz.gov/council/meeting-information/agendas-minutes">Scottsdale City Council agendas</a> · <a href="https://mesa.legistar.com/Legislation.aspx">Mesa City Council (Legistar)</a>. Public records under A.R.S. Title 4.</p>
</body></html>"""
(ROOT / "site").mkdir(exist_ok=True)
(ROOT / "site" / "index.html").write_text(html)
print(f"site built: {len(venues)} new venues, {len(transfers)} transfers, {len(retail)} retail")
"""Build site/index.html from data/filings.json. Static, no JS, fast to index."""
import json
from datetime import datetime, timezone
from pathlib import Path
from html import escape

ROOT = Path(__file__).parent
filings = json.loads((ROOT / "data" / "filings.json").read_text()) if (ROOT / "data" / "filings.json").exists() else {}
active = [v for v in filings.values() if v.get("active")]
CITIES = ["Phoenix", "Scottsdale"]
venues = sorted([v for v in active if v["is_new_venue"]], key=lambda v: v.get("first_seen", ""), reverse=True)
transfers = sorted([v for v in active if not v["is_new_venue"] and v["category"] not in ("beer_wine_store", "liquor_store", "other")], key=lambda v: v["name"])
retail = sorted([v for v in active if v["category"] in ("beer_wine_store", "liquor_store")], key=lambda v: v["name"])
updated = datetime.now(timezone.utc).strftime("%B %d, %Y")

LABEL = {"restaurant": "Restaurant", "bar": "Bar", "beer_wine_bar": "Beer & wine bar", "hotel": "Hotel",
         "private_club": "Private club", "microbrewery": "Brewery", "tasting_room": "Tasting room",
         "beer_wine_store": "Beer & wine retail", "liquor_store": "Liquor store", "other": "Other"}


def row(v):
    lbl = "application" if v.get("city") == "Phoenix" else "council agenda"
    pdf = f' · <a href="{escape(v["pdf_application"])}">{lbl}</a>' if v.get("pdf_application") else ""
    where = f'{escape(v["address"])}, {escape(v.get("city", "Phoenix"))}'
    if v.get("district"):
        where += f' · District {v["district"]}'
    when = escape(v["comment_deadline"].replace(" 5:00 PM", ""))
    when = ("comment period ends " + when) if v.get("city") == "Phoenix" else when
    return (f'<li><strong>{escape(v["name"])}</strong> <span class="tag">{LABEL.get(v["category"], v["category"])}</span>'
            f'<span class="tag">{escape(v.get("city", "Phoenix"))}</span><br>{where} · {escape(v["type"])} · {when}{pdf}</li>')


html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>New Restaurants &amp; Bars Opening Soon in Phoenix &amp; Scottsdale, AZ ({datetime.now().year}) — Liquor License Tracker</title>
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
<h1>New restaurants &amp; bars opening soon in Phoenix &amp; Scottsdale</h1>
<p class="muted">Sourced daily from City of Phoenix liquor license filings and Scottsdale City Council agendas. A "New" application usually means a venue 1–6 months from opening. Updated {updated}. Not affiliated with the City of Phoenix.</p>
<div class="cta"><strong>Sell to restaurants and bars?</strong> Get every new filing in your inbox each week, with applicant details and address, before they open. <a href="#subscribe">Weekly alert for vendors →</a></div>
<h2>{len(venues)} new venues pending</h2><ul>{''.join(row(v) for v in venues) or '<li class="muted">None currently listed.</li>'}</ul>
<p class="muted">By city: {' · '.join(f"{c} {sum(1 for v in venues if v.get('city')==c)}" for c in CITIES)}</p>
<h2>Ownership changes at existing venues ({len(transfers)})</h2><ul>{''.join(row(v) for v in transfers)}</ul>
<h2>Retail beer, wine &amp; liquor ({len(retail)})</h2><ul>{''.join(row(v) for v in retail)}</ul>
<h2 id="subscribe">Weekly vendor alert</h2>
<p>Coming soon. For now, the raw data is at <a href="data/new.json">data/new.json</a> and <a href="data/filings.json">data/filings.json</a>.</p>
<p class="muted">Sources: <a href="https://www.phoenix.gov/administration/departments/cityclerk/programs-services/license-services/new-applications.html">City of Phoenix, Newly Received Liquor License Applications</a> · <a href="https://ww2.scottsdaleaz.gov/council/meeting-information/agendas-minutes">Scottsdale City Council agendas</a>. Public records under A.R.S. Title 4.</p>
</body></html>"""
(ROOT / "site").mkdir(exist_ok=True)
(ROOT / "site" / "index.html").write_text(html)
print(f"site built: {len(venues)} new venues, {len(transfers)} transfers, {len(retail)} retail")
