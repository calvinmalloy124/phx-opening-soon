"""
Daily cold-outreach sender. Reads outreach/sequence.md templates and data/vendors_enriched.csv,
sends the next step for each vendor via Gmail SMTP (hello@), paces itself, logs to data/outreach_log.csv.
Env: GMAIL_USER (hello@liquorlicenseleads.com), GMAIL_APP_PASSWORD, DAILY_LIMIT (default 10)
Steps: 1 on day 0, 2 on day 7, 3 on day 16. Never emails a vendor with status=stop or replied.
"""
import csv, json, os, re, smtplib, ssl, sys, time
from datetime import date, timedelta
from email.message import EmailMessage

USER = os.environ.get("GMAIL_USER", "hello@liquorlicenseleads.com"); PW = os.environ.get("GMAIL_APP_PASSWORD", "")
LIMIT = int(os.environ.get("DAILY_LIMIT", "10"))
LOG = "data/outreach_log.csv"; VEND = "data/vendors_enriched.csv"
FROM_NAME = "Calvin, Liquor License Leads"
STEP_DAYS = {1: 0, 2: 7, 3: 16}


def templates():
    md = open("outreach/sequence.md").read()
    out = {}
    for m in re.finditer(r"## Email (\d) .*?subject: (.+?)\n(.*?)(?=\n## |\Z)", md, re.S):
        out[int(m.group(1))] = (m.group(2).strip(), m.group(3).strip())
    return out


def leads():
    f = json.load(open("data/filings.json")); today = date.today()
    act = [v for v in f.values() if v.get("active") and v.get("is_new_venue") and v.get("category") in ("restaurant", "bar", "beer_wine_bar", "microbrewery")]
    act.sort(key=lambda v: v.get("first_seen", ""), reverse=True)
    fmt = lambda v: f"{v['name']} ({ {'restaurant':'restaurant','bar':'bar','beer_wine_bar':'beer & wine bar','microbrewery':'brewery'}[v['category']] }), {v.get('city','')}" + (f" — applicant {v['agent']}" if v.get("agent") else "")
    week = (today - timedelta(days=7)).isoformat()
    owners = [v for v in f.values() if v.get("active") and not v.get("is_new_venue") and (v.get("first_seen") or "")[:10] >= week]
    return [fmt(v) for v in act[:3]], len([v for v in act if (v.get("first_seen") or "")[:10] >= week]), len(owners)


def fill(t, r, l3, wk, ow):
    first = (r.get("contact_first") or "").strip()
    t = t.replace("{first}, ", first + ", " if first else "Hi, ").replace("{first}", first or "Hi")
    cat = r["category"]; cat = cat.upper() if cat.lower() in ("pos", "cpa") else cat.lower()
    return (t.replace("{company}", r["company"]).replace("{category}", cat)
             .replace("{lead1}", l3[0] if len(l3) > 0 else "").replace("{lead2}", l3[1] if len(l3) > 1 else "").replace("{lead3}", l3[2] if len(l3) > 2 else "")
             .replace("{week_count}", str(wk)).replace("{owner_count}", str(ow)))


def main():
    if not PW:
        print("GMAIL_APP_PASSWORD not set; skipping sends"); return
    if not os.path.exists(VEND):
        print("no vendors_enriched.csv yet"); return
    T = templates(); l3, wk, ow = leads(); today = date.today()
    vendors = list(csv.DictReader(open(VEND)))
    log = list(csv.DictReader(open(LOG))) if os.path.exists(LOG) else []
    sent_by = {}
    for row in log: sent_by.setdefault(row["email"], {})[int(row["step"])] = row["date"]
    queue = []
    for r in vendors:
        e = r.get("email", "").strip()
        if not e or r.get("status") in ("stop", "replied", "bounced"): continue
        hist = sent_by.get(e, {})
        nxt = 1 if 1 not in hist else 2 if 2 not in hist else 3 if 3 not in hist else None
        if nxt is None: continue
        if nxt > 1 and (today - date.fromisoformat(hist[nxt - 1])).days < STEP_DAYS[nxt] - STEP_DAYS[nxt - 1]: continue
        queue.append((r, nxt))
    queue.sort(key=lambda x: -x[1])   # follow-ups first
    ctx = ssl.create_default_context(); n = 0
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as s:
        s.login(USER, PW)
        for r, step in queue[:LIMIT]:
            subj, body = T[step]
            msg = EmailMessage(); msg["From"] = f"{FROM_NAME} <{USER}>"; msg["To"] = r["email"]; msg["Subject"] = fill(subj, r, l3, wk, ow)
            msg.set_content(fill(body, r, l3, wk, ow))
            s.send_message(msg); n += 1
            log.append({"date": today.isoformat(), "email": r["email"], "company": r["company"], "step": step})
            time.sleep(45)
    with open(LOG, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "email", "company", "step"]); w.writeheader(); w.writerows(log)
    print(f"sent {n} (limit {LIMIT}); queued {len(queue)}")


if __name__ == "__main__":
    main()
