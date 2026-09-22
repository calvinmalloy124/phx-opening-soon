"""
Send the free weekly roundup and the paid daily Vendor Alert through Resend,
using beehiiv only as the subscriber list of record (read via API).

Env: BEEHIIV_API_KEY, BEEHIIV_PUB_ID, RESEND_KEY
Usage: python send_alerts.py weekly | daily
"""
import json, os, sys, time
from datetime import date
import requests

BKEY = os.environ["BEEHIIV_API_KEY"]; PUB = os.environ["BEEHIIV_PUB_ID"]; RKEY = os.environ["RESEND_KEY"]
FROM_FREE = "PHX Opening Soon <alerts@liquorlicenseleads.com>"
FROM_PAID = "Vendor Alert <alerts@liquorlicenseleads.com>"
REPLY_TO = "hello@liquorlicenseleads.com"
SITE = "https://liquorlicenseleads.com/"
UPGRADE = "https://phxopeningsoon.beehiiv.com/upgrade"
MANAGE = "https://phxopeningsoon.beehiiv.com/subscribe"   # beehiiv handles unsubscribe/manage
CAT = {"restaurant": "Restaurant", "bar": "Bar", "beer_wine_bar": "Beer & wine bar", "hotel": "Hotel", "microbrewery": "Brewery", "tasting_room": "Tasting room", "private_club": "Private club"}


MARICOPA_CITIES = {"phoenix", "scottsdale", "mesa", "tempe", "chandler", "gilbert", "glendale", "peoria", "goodyear", "avondale", "surprise", "buckeye", "queen creek", "cave creek", "carefree", "fountain hills", "paradise valley", "litchfield park", "tolleson", "el mirage", "youngtown", "wickenburg", "guadalupe", "gila bend", "sun city", "sun city west", "anthem", "laveen", "ahwatukee", "new river", "rio verde", "san tan valley"}


def in_scope(v, tier):
    """$29 'Vendor Alert' = Maricopa County (Phoenix metro). 'Arizona Statewide' = everything."""
    if "statewide" in (tier or "").lower() or "arizona" in (tier or "").lower(): return True
    county = (v.get("county") or "").strip().lower()
    if county: return county == "maricopa"
    return (v.get("city") or "").strip().lower() in MARICOPA_CITIES


def subscribers(premium_only):
    """Active beehiiv subscribers as (email, tier); premium tiers only if premium_only."""
    out, page = [], 1
    while True:
        r = requests.get(f"https://api.beehiiv.com/v2/publications/{PUB}/subscriptions",
                         params={"status": "active", "limit": 100, "page": page, "expand[]": "stats"},
                         headers={"Authorization": f"Bearer {BKEY}"}, timeout=60)
        r.raise_for_status(); j = r.json()
        for s in j.get("data", []):
            tier = (s.get("subscription_tier") or "free").lower()
            if premium_only and tier == "free": continue
            out.append((s["email"], tier))
        if page >= j.get("total_pages", 1): break
        page += 1
    return out


def rows(recs, paid):
    out = []
    for r in sorted(recs, key=lambda x: (x.get("city", ""), x.get("name", ""))):
        kind = CAT.get(r.get('category'), 'Venue')
        if not r.get("is_new_venue"): kind += " · ownership change"
        loc = r.get('city','') + (f" ({r['county']} Co.)" if r.get('county') and (r['county'] or '').lower() != 'maricopa' else "")
        if r.get("type_unknown"): kind += " (type pending)"
        line = f"<li><b>{r['name']}</b> — {kind} · {loc}"
        if paid:
            if r.get("address"): line += f" · {r['address']}"
            if r.get("agent"): line += f" · <b>applicant/agent: {r['agent']}</b>"
            if r.get("phone"): line += f" · {r['phone']}"
            if r.get("email"): line += f" · {r['email']}"
            if r.get("instagram"): line += f" · <a href='{r['instagram']}'>Instagram</a>"
            if r.get("website"): line += f" · <a href='{r['website']}'>site</a>"
            if r.get("pdf_application"): line += f" · <a href='{r['pdf_application']}'>record</a>"
        out.append(line + "</li>")
    return "\n".join(out)


def build(kind):
    from datetime import timedelta
    f = json.load(open("data/filings.json"))
    today = date.today()
    week_ago = (today - timedelta(days=7)).isoformat()
    active = [v for v in f.values() if v.get("active")]
    venues = [v for v in active if v.get("is_new_venue") and (v.get("first_seen") or "")[:10] >= week_ago]
    owner_changes = [v for v in active if not v.get("is_new_venue") and v.get("category") not in ("beer_wine_store", "liquor_store", "other")]
    owner_week = [v for v in owner_changes if (v.get("first_seen") or "")[:10] >= week_ago]
    foot = f"<p style='color:#888;font-size:12px'>You're getting this because you subscribed at phxopeningsoon.beehiiv.com. <a href='{MANAGE}'>Manage or unsubscribe</a>. PHX Opening Soon · Phoenix, AZ</p>"
    if kind == "daily":
        newf = json.load(open("data/new.json")) if os.path.exists("data/new.json") else []
        new_v = [r for r in newf if r.get("is_new_venue")]
        new_o = [r for r in newf if not r.get("is_new_venue") and r.get("category") not in ("beer_wine_store", "liquor_store", "other")]
        if not new_v and not new_o: return None
        return ("daily", new_v, new_o, foot), None, FROM_PAID, True
    by_city = {}
    for r in venues: by_city.setdefault(r.get("city", "Other"), []).append(r)
    subj = f"{len(venues)} new restaurants and bars filed this week in Arizona"
    teaser = f"<p style='border:1px solid #ddd;padding:10px;border-radius:6px'><b>Sell to restaurants?</b> Vendor Alert subscribers got each of these the morning it filed, with the address, the applicant's name, and the record" + (f", plus <b>{len(owner_week)} ownership change{'s' if len(owner_week)!=1 else ''}</b> at existing venues this week" if owner_week else "") + f". <a href='{UPGRADE}'>$29/month, cancel anytime →</a></p>"
    html = teaser + "<p>Restaurants, bars and coffee shops that filed for a liquor license this week. They usually open 30–90 days after filing.</p>"
    shown = sorted(venues, key=lambda x: x.get("first_seen", ""), reverse=True)[:10]
    by_city = {}
    for r in shown: by_city.setdefault(r.get("city", "Other"), []).append(r)
    for city, rs in sorted(by_city.items()): html += f"<h3>{city} ({len(rs)})</h3><ul>{rows(rs, False)}</ul>"
    if len(venues) > 10: html += f"<p><b>{len(venues) - 10} more filed this week.</b> Vendor Alert subscribers have all of them, with address, applicant, phone and email: <a href='{UPGRADE}'>subscribe</a>.</p>"
    html += f"<p>Board: <a href='{SITE}'>{SITE}</a></p>{foot}"
    return subj, html, FROM_FREE, False


SEEN = "data/paid_seen.json"

def welcome_new_paid():
    """Send the full backlog (all active leads, full contacts) to premium subscribers we haven't welcomed yet."""
    seen = set(json.load(open(SEEN))) if os.path.exists(SEEN) else set()
    paid = subscribers(premium_only=True)
    new = [(e, t) for e, t in paid if e not in seen]
    if not new:
        print("welcome: no new paid subscribers"); return
    f = json.load(open("data/filings.json"))
    for email, tier in new:
      active = [v for v in f.values() if v.get("active") and v.get("category") not in ("beer_wine_store", "liquor_store", "other") and in_scope(v, tier)]
      venues = [v for v in active if v.get("is_new_venue")]; owners = [v for v in active if not v.get("is_new_venue")]
      html = (f"<p>Welcome to the {tier}. Here's everything currently on the board so you can start today: "
            f"<b>{len(venues)} new venues</b> and <b>{len(owners)} ownership changes</b> from the last ~45 days, with the applicant, phone and email wherever the public record has them. "
            f"From tomorrow you'll get each new filing the morning it appears.</p>")
      by_city = {}
      for v in venues: by_city.setdefault(v.get("city", "Other"), []).append(v)
      for city, rs in sorted(by_city.items()): html += f"<h3>{city} ({len(rs)})</h3><ul>{rows(rs, True)}</ul>"
      if owners: html += f"<h3>Ownership changes ({len(owners)})</h3><ul>{rows(owners, True)}</ul>"
      html += f"<p>Reply to this email with questions, corrections, or a city you want added. Manage your subscription: <a href='{MANAGE}'>here</a>.</p>"
      send(f"Your starting board: {len(venues)} venues and {len(owners)} ownership changes", html, FROM_PAID, [email])
    json.dump(sorted(seen | {e for e, _ in new}), open(SEEN, "w"))
    print(f"welcome: sent backlog to {len(new)} new paid subscriber(s)")


def daily_html(new_v, new_o, foot, tier):
    v = [r for r in new_v if in_scope(r, tier)]; o = [r for r in new_o if in_scope(r, tier)]
    if not v and not o: return None, None
    scope = "across Arizona" if ("statewide" in (tier or "").lower() or "arizona" in (tier or "").lower()) else "in the Phoenix metro"
    today = date.today()
    subj = f"{len(v)} new venue{'s' if len(v)!=1 else ''}" + (f", {len(o)} ownership change{'s' if len(o)!=1 else ''}" if o else "") + f" {scope} — {today:%b %d}"
    html = f"<p>Liquor-license filings accepted {scope} this morning.</p>"
    if v: html += f"<h3>New venues ({len(v)})</h3><ul>{rows(v, True)}</ul>"
    if o: html += f"<h3>Ownership changes ({len(o)})</h3><p style='color:#666'>New owners re-bid every vendor contract.</p><ul>{rows(o, True)}</ul>"
    if scope != "across Arizona": html += f"<p style='color:#666'>Want Tucson, Flagstaff, Yuma and the rest of the state too? <a href='{UPGRADE}'>Arizona Statewide, $79/month</a>.</p>"
    html += f"<p>Reply to this email if a lead was wrong or you want a city added.</p>{foot}"
    return subj, html


def send(subj, html, sender, to):
    # Resend batch endpoint: up to 100 messages per call
    for i in range(0, len(to), 100):
        batch = [{"from": sender, "to": [e], "reply_to": REPLY_TO, "subject": subj, "html": html} for e in to[i:i+100]]
        r = requests.post("https://api.resend.com/emails/batch", headers={"Authorization": f"Bearer {RKEY}", "Content-Type": "application/json"}, json=batch, timeout=60)
        print(r.status_code, r.text[:200]); r.raise_for_status(); time.sleep(1)


if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "weekly"
    if kind == "welcome":
        welcome_new_paid(); sys.exit(0)
    b = build(kind)
    if b is None: print("no new venues today; nothing sent"); sys.exit(0)
    subj, html, sender, premium = b
    test_to = os.environ.get("TEST_TO", "").strip()
    subs = [(test_to, "Arizona Statewide")] if test_to else subscribers(premium_only=premium)
    print(f"{kind}: {len(subs)} recipients" + (" (TEST MODE)" if test_to else ""))
    if not subs: sys.exit(0)
    if isinstance(subj, tuple) and subj[0] == "daily":
        _, new_v, new_o, foot = subj
        by_tier = {}
        for e, t in subs: by_tier.setdefault(t, []).append(e)
        for t, emails in by_tier.items():
            s2, h2 = daily_html(new_v, new_o, foot, t)
            if s2: send(s2, h2, sender, emails); print(f"  tier {t}: {len(emails)}")
            else: print(f"  tier {t}: nothing in scope today")
    else:
        send(subj, html, sender, [e for e, _ in subs])
