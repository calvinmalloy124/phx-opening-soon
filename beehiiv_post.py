"""
Publish the weekly roundup (free) and the daily vendor alert (paid) to beehiiv.

Env:  BEEHIIV_API_KEY, BEEHIIV_PUB_ID   (GitHub Actions secrets)
Usage: python beehiiv_post.py weekly | daily
Free post  = public, sent to all subscribers, no agent names.
Paid post  = premium audience only, includes agent names + council link.
"""
import json, os, sys
from datetime import date, datetime, timedelta
import requests

KEY = os.environ["BEEHIIV_API_KEY"]; PUB = os.environ["BEEHIIV_PUB_ID"]
API = f"https://api.beehiiv.com/v2/publications/{PUB}/posts"
SITE = "https://calvinmalloy124.github.io/phx-opening-soon/"
UPGRADE = "https://phxopeningsoon.beehiiv.com/upgrade"
CAT = {"restaurant": "Restaurant", "bar": "Bar", "beer_wine_bar": "Beer & wine bar", "hotel": "Hotel", "microbrewery": "Brewery", "tasting_room": "Tasting room", "private_club": "Private club"}


def load():
    f = json.load(open("data/filings.json"))
    return [v for v in f.values() if v.get("active") and v.get("is_new_venue")]


def rows(recs, paid):
    out = []
    for r in sorted(recs, key=lambda x: (x.get("city", ""), x.get("name", ""))):
        line = f"<li><b>{r['name']}</b> — {CAT.get(r.get('category'), 'Venue')} · {r.get('address','')} · {r.get('city','')}"
        if paid:
            if r.get("agent"): line += f" · agent: {r['agent']}"
            if r.get("pdf_application"): line += f" · <a href='{r['pdf_application']}'>filing</a>"
        out.append(line + "</li>")
    return "\n".join(out)


def build(kind):
    recs = load(); today = date.today()
    if kind == "daily":
        new = json.load(open("data/new.json")) if os.path.exists("data/new.json") else []
        new = [r for r in new if r.get("is_new_venue")]
        if not new: return None
        title = f"{len(new)} new venue filings — {today:%b %d}"
        body = f"<p>New restaurant/bar liquor-license filings found this morning in Phoenix, Scottsdale and Mesa.</p><ul>{rows(new, True)}</ul><p>Full board: <a href='{SITE}'>{SITE}</a></p>"
        return dict(title=title, body=body, audience="premium", public=False)
    by_city = {}
    for r in recs: by_city.setdefault(r.get("city", "Other"), []).append(r)
    title = f"{len(recs)} restaurants and bars opening soon in the Valley — week of {today:%b %d}"
    body = "<p>Every restaurant, bar and coffee shop that filed for a liquor license in the last few weeks. They usually open 30–90 days after filing.</p>"
    for city, rs in sorted(by_city.items()):
        body += f"<h3>{city} ({len(rs)})</h3><ul>{rows(rs, False)}</ul>"
    body += f"<p>Sell to restaurants? The <a href='{UPGRADE}'>Vendor Alert</a> sends these daily with the applicant's agent name, for $29/month.</p><p>Live board: <a href='{SITE}'>{SITE}</a></p>"
    return dict(title=title, body=body, audience="free", public=True)


def post(p):
    payload = {"title": p["title"], "body_content": p["body"], "status": "confirmed",
               "email_settings": {"should_send_email": True}, "web_settings": {"is_public": p["public"]},
               "audience": "premium" if p["audience"] == "premium" else "free",
               "scheduled_at": (datetime.utcnow() + timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%SZ")}
    r = requests.post(API, headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}, json=payload, timeout=60)
    print(r.status_code, r.text[:300]); r.raise_for_status()


if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "weekly"
    p = build(kind)
    if p is None: print("nothing new today; no daily post"); sys.exit(0)
    post(p)
