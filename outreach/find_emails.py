"""
Find a contact email for each vendor in data/vendors.csv.
Strategy (all public): Brave search "<company> <city>" -> company site -> fetch home + /contact + /about
-> collect mailto: and visible emails -> prefer sales@/info@/hello@/contact@, else first on-domain email.
Writes data/vendors_enriched.csv with website,email,status. Runs in GitHub Actions (needs BRAVE_API).
"""
import csv, os, re, time, requests

BRAVE = os.environ.get("BRAVE_KEY") or os.environ.get("BRAVE_API", "")
H = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PREF = ("sales", "info", "hello", "contact", "office", "team", "support", "admin")
SKIP = ("yelp.", "facebook.", "linkedin.", "instagram.", "bbb.org", "manta.", "yellowpages", "mapquest", "google.", "indeed.", "glassdoor", "zoominfo", "dnb.", "waze.", "visitphoenix", "experiencescottsdale", "beveragetradenetwork", "chamberofcommerce", "buzzfile", "opencorporates", "bizapedia", "wikipedia", "crunchbase", "thomasnet", "yellowbook", "superpages", "nextdoor", "angi.", "homeadvisor", "houzz", "porch.", "birdeye", "trustpilot", "sitejabber", "azcentral", "phoenixnewtimes", "bizjournals", "prnewswire", "businesswire", "restaurantbusinessonline", "nrn.com", "qsrmagazine")
STOP = {"the", "and", "of", "inc", "llc", "co", "company", "corp", "services", "service", "group", "arizona", "az", "phoenix", "scottsdale", "mesa", "tempe", "chandler", "gilbert", "glendale", "restaurant", "supply", "foods", "food", "distributors", "distributor", "distributing", "wholesale", "insurance", "agency", "cleaning", "hood", "linen", "linens", "refrigeration", "payroll", "signs", "sign", "signage", "pest", "control", "produce", "meat", "seafood", "coffee", "roasters", "fire", "protection", "kitchen", "commercial", "real", "estate", "cpa", "accounting", "tax", "marketing", "media", "systems", "system", "pos", "point", "sale", "solutions"}
# companies whose generic inbox is a black hole: skip the sequence, flag for the regional-manager route
NATIONAL = ("us foods", "sysco", "southern glazer", "hensley", "young's market", "breakthru", "cintas", "ecolab", "performance foodservice", "shamrock", "paycom", "alsco", "fastsigns", "restaurant depot", "chefs' warehouse", "toast", "square", "clover")

def _tokens(name):
    words = re.findall(r"[a-z0-9]+", name.lower())
    toks = {w for w in words if len(w) >= 3 and w not in STOP}
    if len(words) >= 3: toks.add("".join(w[0] for w in words))
    return toks

def _relevant(url, company):
    toks = _tokens(company)
    if not toks: return True
    m = re.match(r"https?://(?:www\.)?([^/]+)", url or "")
    if not m: return False
    host = m.group(1).split(".")[0].lower().replace("-", "")
    return any(t in host for t in toks)


def brave(q):
    r = requests.get("https://api.search.brave.com/res/v1/web/search", params={"q": q, "count": 6, "country": "us"},
                     headers={"Accept": "application/json", "X-Subscription-Token": BRAVE}, timeout=30)
    return [x["url"] for x in r.json().get("web", {}).get("results", [])] if r.ok else []


def site_for(company, city):
    for u in brave(f"{company} {city} AZ"):
        if not any(s in u.lower() for s in SKIP) and _relevant(u, company): return u.split("?")[0]
    return ""


def emails_on(site):
    found = set(); base = re.match(r"https?://[^/]+", site).group(0)
    dom = base.split("//")[1].replace("www.", "")
    for path in ("", "/contact", "/contact-us", "/about", "/about-us"):
        try:
            r = requests.get(base + path, headers=H, timeout=20)
            for e in EMAIL.findall(r.text.replace("[at]", "@")):
                e = e.lower()
                if dom in e or e.endswith(dom): found.add(e)
        except Exception: pass
        time.sleep(1)
    return sorted(found, key=lambda e: (0 if e.split("@")[0] in PREF else 1, e))


def main():
    rows = list(csv.DictReader(open("data/vendors.csv")))
    done = {r["company"]: r for r in csv.DictReader(open("data/vendors_enriched.csv"))} if os.path.exists("data/vendors_enriched.csv") else {}
    out = []
    for r in rows:
        if r["company"] in done: out.append(done[r["company"]]); continue
        if any(n in r["company"].lower() for n in NATIONAL):
            out.append({**r, "website": "", "email": "", "status": "national"}); continue
        site = site_for(r["company"], r["city"]); em = emails_on(site) if site else []
        out.append({**r, "website": site, "email": em[0] if em else "", "status": "ready" if em else "no-email"})
        print(r["company"], "->", site, em[:1])
        if len(out) - len(done) >= 25: break   # gentle: 25 per run
    with open("data/vendors_enriched.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["category", "company", "phone", "city", "website", "email", "status"]); w.writeheader(); w.writerows(out + [done[c] for c in done if c not in {o["company"] for o in out}])


if __name__ == "__main__":
    main()
