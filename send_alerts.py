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


def subscribers(premium_only):
    """Active beehiiv subscribers; premium tier only if premium_only."""
    out, page = [], 1
    while True:
        r = requests.get(f"https://api.beehiiv.com/v2/publications/{PUB}/subscriptions",
                         params={"status": "active", "limit": 100, "page": page, "expand[]": "stats"},
                         headers={"Authorization": f"Bearer {BKEY}"}, timeout=60)
        r.raise_for_status(); j = r.json()
        for s in j.get("data", []):
            tier = (s.get("subscription_tier") or "free").lower()
            if premium_only and tier == "free": continue
            out.append(s["email"])
        if page >= j.get("total_pages", 1): break
        page += 1
    return out


def rows(recs, paid):
    out = []
    for r in sorted(recs, key=lambda x: (x.get("city", ""), x.get("name", ""))):
        kind = CAT.get(r.get('category'), 'Venue')
        if not r.get("is_new_venue"): kind += " · ownership change"
        line = f"<li><b>{r['name']}</b> — {kind} · {r.get('city','')}"
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
        subj = f"{len(new_v)} new venue{'s' if len(new_v)!=1 else ''}" + (f", {len(new_o)} ownership change{'s' if len(new_o)!=1 else ''}" if new_o else "") + f" — {today:%b %d}"
        html = f"<p>Liquor-license filings found this morning in Phoenix, Scottsdale and Mesa.</p>"
        if new_v: html += f"<h3>New venues ({len(new_v)})</h3><ul>{rows(new_v, True)}</ul>"
        if new_o: html += f"<h3>Ownership changes ({len(new_o)})</h3><p style='color:#666'>New owners re-bid every vendor contract.</p><ul>{rows(new_o, True)}</ul>"
        html += f"<p>Reply to this email if a lead was wrong or you want a city added.</p>{foot}"
        return subj, html, FROM_PAID, True
    by_city = {}
    for r in venues: by_city.setdefault(r.get("city", "Other"), []).append(r)
    subj = f"{len(venues)} new restaurants and bars filed this week in the Valley"
    teaser = f"<p style='border:1px solid #ddd;padding:10px;border-radius:6px'><b>Sell to restaurants?</b> Vendor Alert subscribers got each of these the morning it filed, with the address, the applicant's name, and the record" + (f", plus <b>{len(owner_week)} ownership change{'s' if len(owner_week)!=1 else ''}</b> at existing venues this week" if owner_week else "") + f". <a href='{UPGRADE}'>$29/month, cancel anytime →</a></p>"
    html = teaser + "<p>Restaurants, bars and coffee shops that filed for a liquor license this week. They usually open 30–90 days after filing.</p>"
    for city, rs in sorted(by_city.items()): html += f"<h3>{city} ({len(rs)})</h3><ul>{rows(rs, False)}</ul>"
    html += f"<p>Full board (7-day delay): <a href='{SITE}'>{SITE}</a></p>{foot}"
    return subj, html, FROM_FREE, False


def send(subj, html, sender, to):
    # Resend batch endpoint: up to 100 messages per call
    for i in range(0, len(to), 100):
        batch = [{"from": sender, "to": [e], "reply_to": REPLY_TO, "subject": subj, "html": html} for e in to[i:i+100]]
        r = requests.post("https://api.resend.com/emails/batch", headers={"Authorization": f"Bearer {RKEY}", "Content-Type": "application/json"}, json=batch, timeout=60)
        print(r.status_code, r.text[:200]); r.raise_for_status(); time.sleep(1)


if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "weekly"
    b = build(kind)
    if b is None: print("no new venues today; nothing sent"); sys.exit(0)
    subj, html, sender, premium = b
    test_to = os.environ.get("TEST_TO", "").strip()
    to = [test_to] if test_to else subscribers(premium_only=premium)
    print(f"{kind}: {len(to)} recipients" + (" (TEST MODE)" if test_to else ""))
    if not to: sys.exit(0)
    send(subj, html, sender, to)
