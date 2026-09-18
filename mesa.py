"""
Mesa liquor-license applications via the Legistar web API (no auth).

    https://webapi.legistar.com/v1/mesa/matters?$filter=MatterTypeName eq 'Liquor License Application' ...

Each matter title reads like:
    "Shima Sushi\n\nA restaurant that serves lunch and dinner is requesting a new Series 12 Restaurant
     License for Sushi Nakano Inc., 1902 East Baseline Road Suite 5 - Leo Nakano, agent. There is no
     existing license at this location. (District 4)"
"""
import re
from datetime import date, datetime, timedelta

import requests

API = "https://webapi.legistar.com/v1/mesa/matters"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PHXOpeningSoon/1.0)", "Accept": "application/json"}
ACTIVE_DAYS = 45
LOOKBACK_DAYS = 120

VENUE_SERIES = {"6": "bar", "7": "beer_wine_bar", "12": "restaurant", "11": "hotel",
                "14": "private_club", "3": "microbrewery", "19": "tasting_room"}
RETAIL_SERIES = {"9": "liquor_store", "10": "beer_wine_store"}

SERIES_RE = re.compile(r"Series\s+(\d+)[A-Z]?\s+([A-Za-z &/-]+?)\s+License", re.I)
FOR_RE = re.compile(r"\bfor\s+(?P<entity>.+?),\s+(?P<address>\d[^-]+?)\s+-\s+(?P<agent>[^,]+?),\s*agent", re.I | re.S)
DIST_RE = re.compile(r"\(District\s+(\d+)\)", re.I)


def classify(body):
    b = " ".join(body.split()).lower()
    if "sampling privileges to their existing" in b or "add sampling" in b:
        return "Added Privilege"
    if "ownership transfer" in b or "acquisition of control" in b:
        return "Ownership Change"
    if "location transfer" in b or "person and location transfer" in b:
        return "Location Transfer"
    if "requesting a new series" in b or "requesting a new" in b:
        return "New"
    return "Other"


def parse_matter(m):
    title = (m.get("MatterTitle") or "").strip()
    parts = title.split("\n", 1)
    name = " ".join(parts[0].split())
    body = " ".join((parts[1] if len(parts) > 1 else title).split())
    s = SERIES_RE.search(body)
    series = s.group(1) if s else ""
    series_label = f"Series {series} - {s.group(2).strip().title()}" if s else ""
    f = FOR_RE.search(body)
    d = DIST_RE.search(body)
    app_type = classify(body)
    agenda = (m.get("MatterAgendaDate") or "")[:10]
    intro = (m.get("MatterIntroDate") or "")[:10]
    return {
        "name": name,
        "address": " ".join(f.group("address").split()) if f else "",
        "city": "Mesa",
        "district": d.group(1) if d else "",
        "series": series,
        "series_label": series_label,
        "type": app_type,
        "comment_deadline": f"Council meeting {agenda}" if agenda else f"Filed {intro}",
        "category": VENUE_SERIES.get(series) or RETAIL_SERIES.get(series) or "other",
        "is_new_venue": app_type == "New" and series in VENUE_SERIES,
        "app_id": m.get("MatterFile") or str(m.get("MatterId")),
        "pdf_application": f"https://mesa.legistar.com/LegislationDetail.aspx?ID={m.get('MatterId')}",
        "pdf_map": "",
        "meeting_date": agenda or intro,
        "entity": f.group("entity").strip() if f else "",
        "agent": f.group("agent").strip() if f else "",
        "request_text": body,
        "outcome": m.get("MatterStatusName") or "",
    }


def is_active(rec, today=None):
    today = today or date.today()
    try:
        md = datetime.strptime(rec["meeting_date"], "%Y-%m-%d").date()
    except Exception:
        return False
    return today <= md + timedelta(days=ACTIVE_DAYS)


def fetch_all():
    since = (date.today() - timedelta(days=LOOKBACK_DAYS)).isoformat()
    params = {"$top": "200", "$orderby": "MatterIntroDate desc",
              "$filter": f"MatterTypeName eq 'Liquor License Application' and MatterIntroDate ge datetime'{since}'"}
    r = requests.get(API, params=params, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return [parse_matter(m) for m in r.json()]


if __name__ == "__main__":
    import json
    print(json.dumps(fetch_all(), indent=1))
