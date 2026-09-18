"""
Phoenix liquor-license filings scraper.

Pulls the 8 council-district HTML fragments behind the City of Phoenix
"Newly Received Liquor License Applications" page, parses each record,
diffs against data/filings.json, and writes:

  data/filings.json      - every filing ever seen (keyed by app id or name+address)
  data/new.json          - filings first seen on this run (what alerts are built from)
  data/run_log.jsonl     - one line per run: counts, errors, timing (read this first each session)

No browser needed. Zero auth. Runs in ~3 seconds.
"""
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = ("https://www.phoenix.gov/administration/departments/cityclerk/programs-services/"
        "license-services/new-applications/_jcr_content/root/container/container-nav/"
        "container-full-width/container-content/accordion/")
# item -> council district (order confirmed from the live page)
ITEMS = {
    "item_1": 1, "item_2": 2, "item_1738104899178": 3, "item_1738104905698": 4,
    "item_1738104913630": 5, "item_1738104918903": 6, "item_1738104924566": 7,
    "item_1738104931542": 8,
}
SUFFIX = "/liquor_license_appli.dynamic.html"
ORIGIN = "https://www.phoenix.gov"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PHXOpeningSoon/1.0)"}

DATA = Path(__file__).parent / "data"
FILINGS = DATA / "filings.json"
NEW = DATA / "new.json"
LOG = DATA / "run_log.jsonl"

# Series that mean "a place to eat or drink is coming" vs retail/other
VENUE_SERIES = {"6": "bar", "7": "beer_wine_bar", "12": "restaurant", "11": "hotel",
                "14": "private_club", "3": "microbrewery", "19": "tasting_room"}
RETAIL_SERIES = {"9": "liquor_store", "10": "beer_wine_store"}


def field(block_text, label):
    m = re.search(rf"{label}:\s*\n\s*([^\n]+)", block_text)
    return m.group(1).strip() if m else ""


def parse_district(html, district):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text).strip()
    # records start with "<name>\n<address>\nDistrict:"
    chunks = re.split(r"(?=\n[^\n]+\n[^\n]+\n\s*District:)", "\n" + text)
    records = []
    # map app-id -> pdf links by scanning anchors
    pdfs = {}
    for a in soup.find_all("a", href=True):
        h = a["href"]
        m = re.search(r"/(\d{5,7})(app|map|list)\.pdf$", h)
        if m:
            pdfs.setdefault(m.group(1), {})[m.group(2)] = ORIGIN + h
    for c in chunks:
        c = c.strip()
        if "District:" not in c:
            continue
        lines = c.split("\n")
        name, address = lines[0].strip(), lines[1].strip()
        series_raw = field(c, "Series")
        series_num = re.search(r"Series\s+(\d+)", series_raw)
        series_num = series_num.group(1) if series_num else ""
        app_type = field(c, "Type")
        deadline = field(c, "Comment period ends")
        rec = {
            "name": name,
            "address": address,
            "city": "Phoenix",
            "district": district,
            "series": series_num,
            "series_label": series_raw,
            "type": app_type,
            "comment_deadline": deadline,
            "category": VENUE_SERIES.get(series_num) or RETAIL_SERIES.get(series_num) or "other",
            "is_new_venue": app_type.lower().startswith("new") and series_num in VENUE_SERIES,
            "app_id": "",
            "pdf_application": "",
            "pdf_map": "",
        }
        # attach pdfs if this record's name slug appears in a pdf path
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        for aid, links in pdfs.items():
            if any(slug[:12] in l.lower() for l in links.values()):
                rec["app_id"] = aid
                rec["pdf_application"] = links.get("app", "")
                rec["pdf_map"] = links.get("map", "")
                break
        key_src = rec["app_id"] or f"{name}|{address}|{series_num}|{app_type}"
        rec["key"] = hashlib.sha1(key_src.encode()).hexdigest()[:12]
        records.append(rec)
    return records


def main():
    t0 = time.time()
    DATA.mkdir(exist_ok=True)
    known = json.loads(FILINGS.read_text()) if FILINGS.exists() else {}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    errors, seen, new = [], [], []
    for item, district in ITEMS.items():
        try:
            r = requests.get(BASE + item + SUFFIX, headers=HEADERS, timeout=30)
            r.raise_for_status()
            recs = parse_district(r.text, district)
            if not recs:
                errors.append(f"district {district}: parsed 0 records (page format changed?)")
            seen.extend(recs)
        except Exception as e:  # noqa
            errors.append(f"district {district}: {e}")
    for rec in seen:
        k = rec["key"]
        if k not in known:
            rec["first_seen"] = now
            new.append(rec)
        known[k] = {**known.get(k, {}), **rec, "last_seen": now}
    # mark records no longer listed (comment window closed)
    live_keys = {r["key"] for r in seen}
    for k, v in known.items():
        v["active"] = k in live_keys
    FILINGS.write_text(json.dumps(known, indent=1, sort_keys=True))
    NEW.write_text(json.dumps(new, indent=1))
    log = {"ts": now, "live": len(seen), "new": len(new), "total_known": len(known),
           "new_venues": sum(r["is_new_venue"] for r in new), "errors": errors,
           "secs": round(time.time() - t0, 1)}
    with LOG.open("a") as f:
        f.write(json.dumps(log) + "\n")
    print(json.dumps(log, indent=1))
    if errors and len(seen) == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
