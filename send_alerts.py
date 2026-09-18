"""
Send the free weekly roundup and the paid daily Vendor Alert.
Subscribers come from beehiiv (read API works on Scale); delivery goes through Resend.

Env: BEEHIIV_API_KEY, BEEHIIV_PUB_ID, RESEND_KEY
Usage: python send_alerts.py weekly | daily
"""
import json, os, sys, time
from datetime import date
import requests

BH_KEY = os.environ["BEEHIIV_API_KEY"]; PUB = os.environ["BEEHIIV_PUB_ID"]; RS_KEY = os.environ["RESEND_KEY"]
FROM = "PHX Opening Soon <alerts@liquorlicenseleads.com>"
REPLY = "hello@liquorlicenseleads.com"
SITE = "https://liquorlicenseleads.com/"
UPGRADE = "https://phxopeningsoon.beehiiv.com/upgrade"
MANAGE = "https://phxopeningsoon.beehiiv.com/subscribe"   # beehiiv hosts unsubscribe/manage
CAT = {"restaurant": "Restaurant", "bar": "Bar", "beer_wine_bar": "Beer & wine bar", "hotel": "Hotel",
       "microbrewery": "Brewery", "tasting_room": "Tasting room", "private_club": "Private club"}


def subscribers():
    """All active subscribers with their tier (free / premium)."""
    out, cursor = [], None
    while True:
        params = {"limit": 100, "status": "active", "expand[]": "stats"}
        if cursor: params["cursor"] = cursor
        r = requests.get(f"https://api.beehiiv.com/v2/publications/{PUB}/subscriptions", params=params,
                         headers={"Authorization": f"Bearer {BH_KEY}"}, timeout=60)
        r.raise_for_status(); j = r.json()
        for s in j.get("data", []):
            out.append({"email": s["email"], "premium": s.get("subscription_tier") == "premium", "id": s.get("id", "")})
        cursor = j.get("next_cursor")
        if not cursor: break
    return out


def esc(s): return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def rows(recs, paid):
    out = []
    for r in sorted(recs, key=lambda x: (x.get("city", ""), x.get("name", ""))):
        line = f"<li style='margin:0 0 10px'><b>{esc(r['name'])}</b> &mdash; {CAT.get(r.get('category'), 'Venue')} &middot; {esc(r.get('address',''))} &middot; {esc(r.get('city',''))}"
        if paid:
            if r.get("agent"): line += f" &middot; <b>agent: {esc(r['agent'])}</b>"
            if r.get("pdf_application"): line += f" &middot; <a href='{esc(r['pdf_application'])}'>record</a>"
        out.append(line + "</li>")
    return "".join(out)


def wrap(title, inner, footer):
    return f"""<div style="font:15px/1.5 -apple-system,Segoe UI,Arial,sans-serif;color:#1a1a1a;max-width:640px;margin:0 auto;padding:24px">
<h1 style="font-size:20px;margin:0 0 16px">{esc(title)}</h1>{inner}
<p style="color:#666;font-size:13px;margin-top:28px">{footer}</p></div>"""


def build(kind):
    f = json.load(open("data/filings.json"))
    venues = [v for v in f.values() if v.get("active") and v.get("is_new_venue")]
    today = date.today()
    if kind == "daily":
        new = [r for r in (json.load(open("data/new.json")) if os.path.exists("data/new.json") else []) if r.get("is_new_venue")]
        if not new: return None, None, None
        title = f"{len(new)} new venue filings — {today:%a %b %d}"
        inner = f"<p>New restaurant/bar liquor-license filings found this morning in Phoenix, Scottsdale and Mesa.</p><ul style='padding-left:18px'>{rows(new, True)}</ul><p>Full board: <a href='{SITE}'>{SITE}</a></p>"
        footer = f"You're receiving the Vendor Alert because you subscribed. Reply to this email with questions. <a href='{MANAGE}'>Manage or cancel</a>."
        return title, wrap(title, inner, footer), "premium"
    by_city = {}
    for r in venues: by_city.setdefault(r.get("city", "Other"), []).append(r)
    title = f"{len(venues)} restaurants and bars opening soon in the Valley"
    inner = "<p>Every restaurant, bar and coffee shop that filed for a liquor license in the last few weeks. They usually open 30–90 days after filing.</p>"
    for city, rs in sorted(by_city.items()):
        inner += f"<h3 style='font-size:16px;margin:20px 0 8px'>{esc(city)} ({len(rs)})</h3><ul style='padding-left:18px'>{rows(rs, False)}</ul>"
    inner += f"<p style='border:1px solid #e5e5e5;border-radius:8px;padding:12px'><b>Sell to restaurants?</b> The <a href='{UPGRADE}'>Vendor Alert</a> sends these every weekday morning with the applicant's agent name, for $29/month.</p><p>Live board: <a href='{SITE}'>{SITE}</a></p>"
    footer = f"You subscribed at phxopeningsoon.beehiiv.com. <a href='{MANAGE}'>Unsubscribe or manage</a>."
    return title, wrap(title, inner, footer), "all"


def send(to, subject, html):
    r = requests.post("https://api.resend.com/emails", headers={"Authorization": f"Bearer {RS_KEY}", "Content-Type": "application/json"},
                      json={"from": FROM, "to": [to], "reply_to": REPLY, "subject": subject, "html": html}, timeout=60)
    ok = r.status_code in (200, 201)
    if not ok: print("  FAIL", to, r.status_code, r.text[:200])
    return ok


if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "weekly"
    subject, html, audience = build(kind)
    if not subject: print("nothing new; no daily send"); sys.exit(0)
    subs = subscribers()
    targets = [s["email"] for s in subs if audience == "all" or s["premium"]]
    print(f"{kind}: {len(subs)} subscribers, sending to {len(targets)}")
    sent = 0
    for t in targets:
        if send(t, subject, html): sent += 1
        time.sleep(0.6)  # stay under Resend's rate limit
    print(f"sent {sent}/{len(targets)}")
    with open("data/send_log.jsonl", "a") as fh:
        fh.write(json.dumps({"ts": date.today().isoformat(), "kind": kind, "targets": len(targets), "sent": sent, "subject": subject}) + "\n")
