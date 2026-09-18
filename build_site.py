"""Build site/index.html from data/filings.json. Static, no JS, fast to index."""
import json
from datetime import datetime, timezone
from pathlib import Path
from html import escape

ROOT = Path(__file__).parent
filings = json.loads((ROOT / "data" / "filings.json").read_text()) if (ROOT / "data" / "filings.json").exists() else {}
from datetime import date as _date, timedelta as _td
_cutoff = (datetime.now(timezone.utc).date() - _td(days=7)).isoformat()
_all_active = [v for v in filings.values() if v.get("active")]
active = list(_all_active)   # public board is live; it shows only the 10 most recent, names and cities
held_back = len([v for v in _all_active if v["is_new_venue"] and (v.get("first_seen") or "")[:10] > _cutoff])
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
    where = escape(v.get("city", "Phoenix"))
    if v.get("district"):
        where += f' · District {v["district"]}'
    when = escape(v["comment_deadline"].replace(" 5:00 PM", ""))
    when = ("comment period ends " + when) if v.get("city") == "Phoenix" else when
    return (f'<li><strong>{escape(v["name"])}</strong> <span class="tag">{LABEL.get(v["category"], v["category"])}</span>'
            f'<span class="tag">{escape(v.get("city", "Phoenix"))}</span><br>{where} · {escape(v["type"])} · {when}</li>')


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
<div class="cta"><strong>Want this every Thursday?</strong> Free weekly email of every restaurant and bar about to open in the Valley. <a href="https://phxopeningsoon.beehiiv.com" rel="noopener">Subscribe free →</a></div>
<div class="cta"><strong>Sell to restaurants and bars?</strong> The <a href="https://phxopeningsoon.beehiiv.com/upgrade" rel="noopener">Vendor Alert</a> emails you every new filing each weekday morning with the applicant's agent name and a link to the record, weeks before the doors open. $29/month, cancel anytime.</div>
<h2>{len(venues)} new venues pending (the 10 most recent, live)</h2>
{f'<p class="cta"><strong>{held_back} more filed in the last 7 days.</strong> Vendor Alert subscribers already have them, with the address, the applicant and a link to the record. <a href="https://phxopeningsoon.beehiiv.com/upgrade" rel="noopener">Get the daily alert →</a></p>' if held_back else ''}<ul>{''.join(row(v) for v in venues[:10]) or '<li class="muted">None currently listed.</li>'}</ul>
{f'<p class="cta"><strong>{len(venues) - 10} more pending</strong> beyond the ten shown. Vendor Alert subscribers get every filing the morning it appears, with address, applicant, phone and email. <a href="https://phxopeningsoon.beehiiv.com/upgrade" rel="noopener">Subscribe \u2192</a></p>' if len(venues) > 10 else ''}
<p class="muted">By city: {' · '.join(f"{c} {sum(1 for v in venues if v.get('city')==c)}" for c in CITIES)}</p>
<h2>Ownership changes at existing venues ({len(transfers)})</h2><p class="muted">New owners re-bid every vendor contract. Vendor Alert subscribers get these the day they file, with names and contacts.</p>
<h2>Retail beer, wine &amp; liquor ({len(retail)})</h2><p class="muted">Included in the Vendor Alert with category tags.</p>
<h2 id="subscribe">Get the alerts</h2>
<p><a href="https://phxopeningsoon.beehiiv.com" rel="noopener">Free weekly roundup</a> for locals · <a href="https://phxopeningsoon.beehiiv.com/upgrade" rel="noopener">Vendor Alert, $29/month</a> for POS reps, distributors, insurers, linen, payroll and anyone else who sells to new restaurants. Data licensing for platforms and multi-market teams: hello@liquorlicenseleads.com.</p>
<p class="muted">Sources: <a href="https://www.phoenix.gov/administration/departments/cityclerk/programs-services/license-services/new-applications.html">City of Phoenix, Newly Received Liquor License Applications</a> · <a href="https://ww2.scottsdaleaz.gov/council/meeting-information/agendas-minutes">Scottsdale City Council agendas</a> · <a href="https://mesa.legistar.com/Legislation.aspx">Mesa City Council (Legistar)</a>. Public records under A.R.S. Title 4.</p>
</body></html>"""
(ROOT / "site" / "phoenix").mkdir(parents=True, exist_ok=True)
html = html.replace('<meta name="viewport"', '<link rel="canonical" href="https://liquorlicenseleads.com/phoenix/">\n<meta name="viewport"')
html = html.replace('<h1>New restaurants', '<p class="muted"><a href="/">liquorlicenseleads.com</a> \u00b7 Phoenix edition</p>\n<h1>New restaurants')
(ROOT / "site" / "phoenix" / "index.html").write_text(html)
print(f"site built: {len(venues)} new venues, {len(transfers)} transfers, {len(retail)} retail")


# ---------------------------------------------------------------------------
# Landing page (site/index.html): sells the Vendor Alert. Sample leads are real,
# recent, and partially redacted.
# ---------------------------------------------------------------------------
def _redact_phone(p):
    d = "".join(ch for ch in (p or "") if ch.isdigit())
    return f"({d[:3]}) {d[3:6]}-\u2022\u2022\u2022\u2022" if len(d) >= 10 else ""

def _redact_email(e):
    if not e or "@" not in e: return ""
    u, dom = e.split("@", 1); return u[:2] + "\u2022\u2022\u2022\u2022@" + dom

_recent = sorted([v for v in _all_active if v["is_new_venue"] and v["category"] in ("restaurant", "bar", "beer_wine_bar", "microbrewery")], key=lambda v: v.get("first_seen", ""), reverse=True)
_score = lambda v: (bool(v.get("phone")) + bool(v.get("email")) + bool(v.get("instagram")) + bool(v.get("agent")) + bool(v.get("website")))
_samples = sorted(_recent, key=lambda v: (-_score(v), v.get("first_seen", "")), reverse=False)[:3]
_week_new = len([v for v in _all_active if v["is_new_venue"] and (v.get("first_seen") or "")[:10] > _cutoff])
_week_own = len([v for v in _all_active if not v["is_new_venue"] and v["category"] not in ("beer_wine_store", "liquor_store", "other") and (v.get("first_seen") or "")[:10] > _cutoff])

import hashlib as _hl
def _scramble(s, keep=2):
    """Same shape as the real value, deterministic, but not the real value (blur is cosmetic; source stays clean)."""
    h = _hl.md5(s.encode()).hexdigest()
    out, hi = [], 0
    for i, ch in enumerate(s):
        if i < keep or not ch.isalnum(): out.append(ch); continue
        d = int(h[hi % 32], 16); hi += 1
        out.append(str(d % 10) if ch.isdigit() else "abcdefghijklmnopqrstuvwxyz"[d % 26])
    return "".join(out)

def _lock(label, real):
    if "@" in real:
        u, dom = real.split("@", 1); fake = _scramble(u, 2) + "@" + dom
    elif label == "phone":
        fake = _scramble(real, 5)
    else:
        fake = _scramble(real, 3)
    return f'<span class="lock" title="Subscribers see this">{label} <span class="blur">{escape(fake)}</span> \U0001F512</span>'

def _sample_card(v):
    bits = [f'<span class="tag">{LABEL.get(v["category"], "Venue")}</span><span class="tag">{escape(v.get("city", ""))}</span>']
    line2 = [escape(v.get("address", ""))]
    if v.get("agent"): line2.append(f'applicant <b>{escape(v["agent"])}</b>')
    line3 = []
    if v.get("phone"): line3.append(_lock("phone", v["phone"]))
    if v.get("email"): line3.append(_lock("email", v["email"]))
    if v.get("instagram"): line3.append(_lock("instagram", "@" + v["instagram"].rstrip("/").split("/")[-1]))
    if v.get("website"): line3.append(_lock("site", v["website"].split("//")[-1].split("/")[0]))
    l3 = f'<div class="muted">{" \u00b7 ".join(line3)}</div>' if line3 else ""
    return f'<div class="lead"><div><strong>{escape(v["name"])}</strong> {" ".join(bits)}</div><div class="muted">{" \u00b7 ".join(x for x in line2 if x)}</div>{l3}<div class="muted small">Filed {escape((v.get("first_seen") or "")[:10])} \u00b7 usually opens 30\u201390 days later</div></div>'

landing_html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Liquor License Leads \u2014 New restaurants and bars before they open (Phoenix, Scottsdale, Mesa)</title>
<meta name="description" content="Every new restaurant and bar liquor-license filing in the Phoenix metro, emailed to you each weekday morning with the applicant's name, phone and email. $29/month.">
<link rel="canonical" href="https://liquorlicenseleads.com/">
<style>
:root{{--bg:#f4f1ec;--card:#fff;--fg:#1f2a2c;--muted:#6b7a7c;--line:#e2ddd5;--acc:#2e6f73;--acc2:#c7813f;--tag:#eef3f2}}
*{{box-sizing:border-box}} body{{margin:0;font:17px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--fg)}}
.wrap{{max-width:900px;margin:0 auto;padding:32px 20px}} a{{color:var(--acc)}}
header{{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:40px}}
.logo{{font-weight:800;letter-spacing:-.02em;font-size:1.15rem;color:var(--fg);text-decoration:none}}
.btn{{display:inline-block;background:var(--acc2);color:#fff;text-decoration:none;font-weight:700;padding:14px 22px;border-radius:10px}}
.btn.alt{{background:var(--acc)}}
h1{{font-size:2.4rem;line-height:1.1;letter-spacing:-.02em;margin:0 0 14px}} h2{{font-size:1.4rem;margin:48px 0 14px}}
.sub{{font-size:1.15rem;color:var(--muted);max-width:640px}}
.lead{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin:10px 0}}
.tag{{font-size:.72rem;background:var(--tag);padding:2px 8px;border-radius:99px;margin-left:6px;color:var(--acc)}}
.muted{{color:var(--muted)}} .small{{font-size:.85rem}}
.blur{{filter:blur(5px);user-select:none;color:var(--fg)}} .lock{{white-space:nowrap}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px}}
.price{{font-size:2.2rem;font-weight:800}} ul{{padding-left:20px}} li{{margin:6px 0}}
.stat{{font-size:2rem;font-weight:800;color:var(--acc)}}
footer{{margin-top:60px;color:var(--muted);font-size:.85rem}}
.embed{{margin-top:8px}} .embed iframe{{max-width:100%}}
@media(max-width:600px){{h1{{font-size:1.9rem}}}}
</style></head><body><div class="wrap">
<header><a class="logo" href="/">Liquor License Leads</a><a class="btn" href="https://phxopeningsoon.beehiiv.com/upgrade" rel="noopener">Get the daily alert \u2192</a></header>

<h1>Know about every new restaurant and bar in the Valley 30\u201390 days before it opens.</h1>
<p class="sub">Every weekday morning: each new liquor-license filing in Phoenix, Scottsdale and Mesa, with the applicant's name, phone and email pulled from the public record. Built for the people who sell to restaurants.</p>
<p><a class="btn" href="https://phxopeningsoon.beehiiv.com/upgrade" rel="noopener">Start for $29/month \u2192</a> &nbsp; <span class="muted small">Cancel anytime. Reply to any email and a person answers.</span></p>
<p class="muted"><b>Day one isn't empty.</b> Your first email is the entire current board: every active filing from the last 45 days ({len(venues) + _week_new} venues and {len(transfers) + _week_own} ownership changes right now) with full contact details, so you can work last month's openings too.</p>

<div class="grid" style="margin-top:32px">
<div class="card"><div class="stat">{len(venues) + _week_new}</div><div class="muted">restaurants &amp; bars pending right now (every filing in Phoenix, Scottsdale &amp; Mesa)</div></div>
<div class="card"><div class="stat">{_week_new}</div><div class="muted">new filings in the last 7 days</div></div>
<div class="card"><div class="stat">{_week_own}</div><div class="muted">ownership changes this week</div></div>
</div>

<h2>What a lead looks like</h2>
<p class="muted">Real filings from the board. Blurred fields are what subscribers unlock.</p>
{"".join(_sample_card(v) for v in _samples)}

<h2>Who this is for</h2>
<div class="grid">
<div class="card"><b>POS &amp; payments</b><br><span class="muted">Toast, Square, Clover, merchant services</span></div>
<div class="card"><b>Distribution</b><br><span class="muted">Food, beer &amp; wine, spirits, coffee, produce</span></div>
<div class="card"><b>Build-out &amp; services</b><br><span class="muted">Insurance, linen, hood cleaning, pest, refrigeration, signage, payroll</span></div>
<div class="card"><b>Money &amp; advice</b><br><span class="muted">SBA lenders, CPAs, license consultants, brokers</span></div>
</div>

<h2>Why the filing date matters</h2>
<p>A restaurant applies for its liquor license months before the sign goes up. That's when the owner is choosing a POS system, signing with a distributor, buying insurance and lining up every other vendor. By the time it's on Instagram, those contracts are signed. Subscribers call first.</p>

<h2>Pricing</h2>
<div class="grid">
<div class="card"><div class="price">$29<span class="muted small">/mo</span></div><b>Vendor Alert</b><ul><li>Every weekday morning</li><li>Phoenix, Scottsdale &amp; Mesa (more cities coming)</li><li>Address, applicant, phone, email, link to the record</li><li>Ownership changes flagged</li><li>Full 45-day backlog on day one</li></ul><a class="btn" href="https://phxopeningsoon.beehiiv.com/upgrade" rel="noopener">Subscribe \u2192</a></div>
<div class="card" id="free"><div class="price">Free</div><b>Thursday roundup</b><ul><li>This week's new venues, names and cities</li><li>For locals who want to know what's coming</li></ul><div class="embed"><script async src="https://subscribe-forms.beehiiv.com/v3/loader.js" data-beehiiv-form="88ab1535-52a2-4a24-947a-40848878c015"></script></div></div>
<div class="card"><div class="price">Teams</div><b>Data licensing</b><ul><li>Multi-market, CSV/API delivery</li><li>Regional and national sales teams</li></ul><a href="mailto:hello@liquorlicenseleads.com">hello@liquorlicenseleads.com</a></div>
</div>

<h2>Where the data comes from</h2>
<p class="muted">City of Phoenix liquor license applications, Scottsdale City Council agendas and Mesa City Council filings, read every morning. Contact details come from the Arizona Department of Liquor Licenses and Control report attached to each application. All public records under A.R.S. Title 4. Browse the <a href="/phoenix/">Phoenix board</a> (the 10 most recent; subscribers get every filing with contacts the morning it appears).</p>

<footer>Liquor License Leads \u00b7 Phoenix, AZ \u00b7 <a href="mailto:hello@liquorlicenseleads.com">hello@liquorlicenseleads.com</a> \u00b7 Not affiliated with any city or the State of Arizona.</footer>
</div></body></html>"""
(ROOT / "site" / "index.html").write_text(landing_html)
print("landing built")


# ---------------------------------------------------------------------------
# RSS feeds for beehiiv RSS-to-Send (Scale plan). One item per run.
# feed_weekly.xml  -> free audience (no agent names)
# feed_daily.xml   -> paid audience (agent names + record links); only when there are new venues
# ---------------------------------------------------------------------------
def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _rows(recs, paid):
    out = []
    for r in sorted(recs, key=lambda x: (x.get("city", ""), x.get("name", ""))):
        line = f"<li><b>{_esc(r['name'])}</b> &#8212; {_esc(CAT_LABEL.get(r.get('category'), 'Venue'))} &#183; {_esc(r.get('address',''))} &#183; {_esc(r.get('city',''))}"
        if paid:
            if r.get("agent"): line += f" &#183; agent: {_esc(r['agent'])}"
            if r.get("pdf_application"): line += f" &#183; <a href='{_esc(r['pdf_application'])}'>record</a>"
        out.append(line + "</li>")
    return "\n".join(out)

CAT_LABEL = {"restaurant": "Restaurant", "bar": "Bar", "beer_wine_bar": "Beer &amp; wine bar", "hotel": "Hotel",
             "microbrewery": "Brewery", "tasting_room": "Tasting room", "private_club": "Private club"}
SITE_URL = "https://liquorlicenseleads.com/"
UPGRADE_URL = "https://phxopeningsoon.beehiiv.com/upgrade"

def _feed(path, title, items):
    import email.utils, time
    now = email.utils.formatdate(time.time(), usegmt=True)
    body = "".join(
        f"<item><title>{_esc(t)}</title><link>{SITE_URL}?d={d}</link><guid isPermaLink='false'>{g}</guid>"
        f"<pubDate>{now}</pubDate><description><![CDATA[{h}]]></description></item>" for t, g, d, h in items)
    xml = (f"<?xml version='1.0' encoding='UTF-8'?><rss version='2.0'><channel><title>{_esc(title)}</title>"
           f"<link>{SITE_URL}</link><description>{_esc(title)}</description><lastBuildDate>{now}</lastBuildDate>{body}</channel></rss>")
    (ROOT / "site" / path).write_text(xml)

def write_feeds(venues, new_venues, today):
    d = today.isoformat()
    by_city = {}
    for r in venues: by_city.setdefault(r.get("city", "Other"), []).append(r)
    html = "<p>Restaurants, bars and coffee shops that filed for a liquor license this week. They usually open 30&#8211;90 days after filing.</p>"
    for city, rs in sorted(by_city.items()):
        html += f"<h3>{_esc(city)} ({len(rs)})</h3><ul>{_rows(rs, False)}</ul>"
    html += f"<p>Sell to restaurants? The <a href='{UPGRADE_URL}'>Vendor Alert</a> sends these every weekday morning with the applicant's agent name, for $29/month.</p><p>Live board: <a href='{SITE_URL}'>{SITE_URL}</a></p>"
    _feed("feed_weekly.xml", "PHX Opening Soon", [(f"{len(venues)} restaurants and bars opening soon in the Valley", f"weekly-{d}", d, html)])
    items = []
    if new_venues:
        h = f"<p>New restaurant/bar liquor-license filings found this morning.</p><ul>{_rows(new_venues, True)}</ul><p>Full board: <a href='{SITE_URL}'>{SITE_URL}</a></p>"
        items = [(f"{len(new_venues)} new venue filings", f"daily-{d}", d, h)]
    _feed("feed_daily.xml", "PHX Opening Soon Vendor Alert", items)



_new = json.loads((ROOT / "data" / "new.json").read_text()) if (ROOT / "data" / "new.json").exists() else []
write_feeds(venues, [r for r in _new if r.get("is_new_venue")], datetime.now(timezone.utc).date())
print("feeds written")

# public, trimmed JSON (no addresses/contacts) for anyone who wants to build on the delayed board
(ROOT / "site" / "data").mkdir(exist_ok=True)
(ROOT / "site" / "data" / "public.json").write_text(json.dumps([{"name": v["name"], "category": v["category"], "city": v.get("city"), "type": v["type"], "first_seen": (v.get("first_seen") or "")[:10]} for v in venues], indent=1))


# thank-you page for the free signup redirect
(ROOT / "site" / "thanks").mkdir(parents=True, exist_ok=True)
(ROOT / "site" / "thanks" / "index.html").write_text("""<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>You're in \u2014 Liquor License Leads</title><meta name=\"robots\" content=\"noindex\"><style>body{{margin:0;font:17px/1.55 system-ui,sans-serif;background:#f4f1ec;color:#1f2a2c}}.wrap{{max-width:640px;margin:0 auto;padding:60px 20px}}a{{color:#2e6f73}}.btn{{display:inline-block;background:#c7813f;color:#fff;text-decoration:none;font-weight:700;padding:14px 22px;border-radius:10px}}</style></head><body><div class=\"wrap\"><h1>You're in.</h1><p>Check your inbox for a welcome email (look in Promotions if it isn't there). Every Thursday you'll get the week's new restaurant and bar filings across the Valley.</p><p><b>Sell to restaurants?</b> The Vendor Alert sends every filing the morning it appears, with the applicant's name, phone and email, plus the full 45-day board on day one.</p><p><a class=\"btn\" href=\"https://phxopeningsoon.beehiiv.com/upgrade\" rel=\"noopener\">Get the daily alert, $29/month \u2192</a></p><p><a href=\"/\">Back to the site</a></p></div></body></html>""")
