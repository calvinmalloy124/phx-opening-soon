"""
Scottsdale liquor-license items from City Council agenda PDFs.

Scottsdale has no standing 'pending applications' page; each application appears as a
consent item on the Council agenda ~10 days before the meeting:

    2. The Dash Liquor License (LL-0057-2026)
    Request: Consider forwarding a recommendation of approval to the Arizona Department of Liquor
    Licenses & Control for a new Series 12 (Restaurant) State liquor license for an existing location with a
    new owner.
    Location: 9619 N. Hayden Road A101-102

We list agenda PDFs from the index page, parse the ones we haven't seen, and emit records in the
same shape as the Phoenix scraper. A record stays 'active' for ACTIVE_DAYS after its meeting date.
"""
import io
import re
from datetime import date, datetime, timedelta

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

INDEX = "https://ww2.scottsdaleaz.gov/council/meeting-information/agendas-minutes"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PHXOpeningSoon/1.0)"}
ACTIVE_DAYS = 45

ITEM_RE = re.compile(
    r"\n\s*\d+\.\s+(?P<name>[^\n]+?)\s+Liquor License\s*\((?P<app>[^)]+)\)\s*"
    r"Request:(?P<req>.*?)Location:\s*(?P<loc>[^\n]+)",
    re.S | re.I,
)
SERIES_RE = re.compile(r"Series\s+(\d+)\s*\(([^)]+)\)", re.I)

VENUE_SERIES = {"6": "bar", "7": "beer_wine_bar", "12": "restaurant", "11": "hotel",
                "14": "private_club", "3": "microbrewery", "19": "tasting_room"}
RETAIL_SERIES = {"9": "liquor_store", "10": "beer_wine_store"}


def classify(req):
    r = " ".join(req.split()).lower()
    if "acquisition of control" in r or "agent" in r and "change" in r:
        return "Acquisition of Control"
    if "location transfer" in r or "new location" in r and "existing owner" in r:
        return "Location Transfer"
    if "new location and owner" in r or "new location and new owner" in r:
        return "New"
    if "existing location with a new owner" in r or "new owner" in r:
        return "Ownership Change"
    if "new series" in r:
        return "New Series"
    return "Other"


def list_agendas():
    html = requests.get(INDEX, headers=HEADERS, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for a in soup.find_all("a", href=True):
        h = a["href"]
        m = re.search(r"/(\d{2})-(\d{2})-(\d{2})-([a-z0-9-]*agenda[a-z0-9-]*)\.pdf$", h, re.I)
        if m and "/20" in h and "special" not in h.lower() and "cfd" not in h.lower():
            mm, dd, yy = m.group(1), m.group(2), m.group(3)
            out.append({"url": h if h.startswith("http") else "https://ww2.scottsdaleaz.gov" + h,
                        "meeting_date": f"20{yy}-{mm}-{dd}"})
    # newest first, de-dupe
    seen, res = set(), []
    for x in sorted(out, key=lambda x: x["meeting_date"], reverse=True):
        if x["url"] not in seen:
            seen.add(x["url"]); res.append(x)
    return res


def pdf_text(url):
    b = requests.get(url, headers=HEADERS, timeout=60).content
    reader = PdfReader(io.BytesIO(b))
    return "\n".join((p.extract_text() or "") for p in reader.pages)


def parse_agenda_text(text, meeting_date, url=""):
    recs = []
    for m in ITEM_RE.finditer("\n" + text):
        name = " ".join(m.group("name").split())
        req = " ".join(m.group("req").split())
        s = SERIES_RE.search(req)
        series = s.group(1) if s else ""
        series_label = f"Series {series} - {s.group(2).strip()}" if s else ""
        app_type = classify(req)
        recs.append({
            "name": name,
            "address": " ".join(m.group("loc").split()),
            "city": "Scottsdale",
            "district": "",
            "series": series,
            "series_label": series_label,
            "type": app_type,
            "comment_deadline": f"Council meeting {meeting_date}",
            "category": VENUE_SERIES.get(series) or RETAIL_SERIES.get(series) or "other",
            "is_new_venue": app_type == "New" and series in VENUE_SERIES,
            "app_id": m.group("app").strip(),
            "pdf_application": url,
            "pdf_map": "",
            "meeting_date": meeting_date,
            "request_text": req,
        })
    return recs


def is_active(rec, today=None):
    today = today or date.today()
    try:
        md = datetime.strptime(rec["meeting_date"], "%Y-%m-%d").date()
    except Exception:
        return False
    return today <= md + timedelta(days=ACTIVE_DAYS)


def fetch_all(max_agendas=6, seen_urls=()):
    """Return (records, agendas_parsed, errors). Only parses agendas not in seen_urls."""
    recs, parsed, errors = [], [], []
    try:
        agendas = list_agendas()[:max_agendas]
    except Exception as e:  # noqa
        return [], [], [f"scottsdale index: {e}"]
    for ag in agendas:
        if ag["url"] in seen_urls:
            continue
        try:
            txt = pdf_text(ag["url"])
            r = parse_agenda_text(txt, ag["meeting_date"], ag["url"])
            recs.extend(r); parsed.append(ag["url"])
        except Exception as e:  # noqa
            errors.append(f"scottsdale {ag['url']}: {e}")
    return recs, parsed, errors


if __name__ == "__main__":
    import json
    r, p, e = fetch_all()
    print(json.dumps({"records": r, "parsed": p, "errors": e}, indent=1))
