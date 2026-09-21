"""Merge data/statewide_pending.csv (DLLC Pending Applications, all of Arizona) into data/filings.json.
Keys: az-<job number>. Skips rows that duplicate a city-scraper record (same normalized name + city).
Dates: accepted date is the real filing date -> first_seen."""
import csv, json, re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
CSV = ROOT / "data" / "statewide_pending.csv"; FIL = ROOT / "data" / "filings.json"
TYPE_MAP = {"restaurant": "restaurant", "bar": "bar", "beer and wine bar": "beer_wine_bar", "hotel / motel": "hotel", "hotel": "hotel",
            "in state microbrewery": "microbrewery", "microbrewery": "microbrewery", "tasting room": "tasting_room", "club": "private_club",
            "liquor store": "liquor_store", "beer and wine store": "beer_wine_store"}
VENUE_WORDS = re.compile(r"\b(restaurant|grill|grille|cafe|caf\u00e9|kitchen|taco|tacos|bbq|barbecue|pizza|pizzeria|sushi|ramen|pho|bistro|brunch|diner|eatery|cantina|cocina|steakhouse|steak|burger|burgers|wings|seafood|mariscos|bar|lounge|saloon|pub|tavern|brew|brewing|brewery|taproom|tap room|winery|distill|cocktail|social club|sports|bakery|coffee|espresso|tea|boba|bagel|deli|wine)\b", re.I)
SKIP_WORDS = re.compile(r"\b(community association|hoa|homeowners|golf club|country club|church|school|hospital|circle k|quiktrip|qt|walgreens|cvs|fry's|safeway|bashas|walmart|target|costco|sam's club|7-eleven|chevron|shell|arco|mobil|market|liquor|convenience)\b", re.I)


def norm(s): return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def classify(row):
    t = (row.get("Type") or "").strip().lower(); name = row.get("Business Name") or ""
    if t in TYPE_MAP: return TYPE_MAP[t]
    if SKIP_WORDS.search(name): return "other"
    if VENUE_WORDS.search(name):
        return "bar" if re.search(r"\b(bar|lounge|saloon|pub|tavern|taproom|tap room)\b", name, re.I) and not re.search(r"restaurant|grill|kitchen", name, re.I) else "restaurant"
    if re.search(r"\b(llc|inc|corp|enterprises|holdings|investments|properties|management|association|foundation|department|city of|town of|county)\b", name, re.I): return "other"
    return "restaurant"   # named business, type not yet assigned by the state -> still a lead; flagged type_unknown


def main():
    if not CSV.exists(): print("no statewide csv"); return
    filings = json.loads(FIL.read_text()) if FIL.exists() else {}
    existing = {(norm(v.get("name")), norm(v.get("city"))) for v in filings.values() if v.get("active")}
    now = datetime.now(timezone.utc).date().isoformat()
    seen_jobs, added, kept = set(), 0, 0
    for row in csv.DictReader(CSV.open(encoding="utf-8-sig")):
        job = (row.get("Job Number") or "").strip()
        if not job: continue
        key = f"az-{job}"; seen_jobs.add(key)
        name = (row.get("Business Name") or "").strip(); city = (row.get("City") or "").strip().title()
        if key in filings: filings[key]["active"] = True; kept += 1; continue
        if (norm(name), norm(city)) in existing: continue   # already covered by a city scraper with richer data
        cat = classify(row)
        accepted = (row.get("Accepted Date") or "")[:10] or now
        filings[key] = {
            "key": key, "name": name, "address": (row.get("Street Address") or "").strip().title(), "city": city,
            "county": (row.get("County") or "").strip(), "zip": (row.get("Zip") or "").strip(), "type": "New" if not (row.get("License Number") or "").strip() else "Transfer",
            "series": "", "category": cat, "is_new_venue": not bool((row.get("License Number") or "").strip()) and cat != "other",
            "entity": (row.get("Licensee") or "").strip().title(), "agent": (row.get("Licensee Name") or "").strip().title(),
            "comment_deadline": f"Accepted {accepted}", "first_seen": accepted, "last_seen": now, "active": True,
            "source": "AZ DLLC pending applications", "pdf_application": "",
            "type_unknown": not (row.get("Type") or "").strip() and not VENUE_WORDS.search(name),
        }
        added += 1
    # deactivate statewide records that dropped off the pending list
    dropped = 0
    for k, v in filings.items():
        if k.startswith("az-") and k not in seen_jobs and v.get("active"): v["active"] = False; dropped += 1
    FIL.write_text(json.dumps(filings, indent=1))
    print(f"statewide merge: +{added} new, {kept} kept, {dropped} dropped; total active {sum(1 for v in filings.values() if v.get('active'))}")


if __name__ == "__main__":
    main()
