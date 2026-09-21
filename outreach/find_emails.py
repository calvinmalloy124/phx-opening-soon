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


TEAM_PATHS = ("/team", "/our-team", "/about", "/about-us", "/meet-the-team", "/staff", "/leadership", "/contact", "/contact-us")
ROLE = re.compile(r"\b(owner|founder|president|ceo|principal|partner|general manager|sales manager|director of sales|vp of sales|vice president of sales|account executive|account manager|sales rep(?:resentative)?|business development|territory manager|regional manager|branch manager|managing partner)\b", re.I)
NAME = re.compile(r"\b([A-Z][a-z]{1,15}) ([A-Z][a-z]{1,20})\b")
NOISE = {"Contact Us", "About Us", "Our Team", "Learn More", "Read More", "Privacy Policy", "Terms Of", "All Rights", "Get Started", "Free Quote", "Call Now", "Follow Us", "Meet The", "Our Story", "Sign Up", "Serving The", "Request Quote"}
NOTNAME = {"Current", "Kitchen", "Hood", "Our", "Your", "The", "Meet", "Learn", "Get", "View", "Open", "Job", "Jobs", "Career", "Careers", "Apply", "Request", "Free", "Best", "Top", "Local", "Family", "Owned", "Serving", "Licensed", "Bonded", "Insured", "Trusted", "Quality", "Service", "Services", "Commercial", "Residential", "Contact", "About", "Home", "Team", "Staff", "Leadership", "Company", "General", "Sales", "Account", "Business", "Regional", "Territory", "Branch", "Managing", "Vice", "President", "Director", "Manager", "Owner", "Founder", "Read", "More", "Click", "Here", "Call", "Email", "Phone", "Office", "Hours", "Monday", "Friday", "Saturday", "Sunday", "Arizona", "Phoenix", "Scottsdale", "Mesa", "Tempe", "Chandler", "Gilbert", "Glendale", "Valley", "North", "South", "East", "West", "New", "Restaurant", "Food", "Fire", "Pest", "Linen", "Sign", "Signs", "Coffee", "Produce", "Meat", "Ice", "Wine", "Beer", "Since", "Years", "Experience", "Proudly", "Locally", "Veteran", "Women", "Certified", "Member", "Partner", "Partners", "Group", "Inc", "Llc", "Customer", "Client", "Clients", "Reviews", "Testimonials", "Gallery", "Blog", "News", "Faq", "Menu", "Search", "Login", "Book", "Schedule", "Now", "Today", "Us", "Me", "We", "Where", "What", "Why", "How", "Who"}


def _ok_name(nm, company):
    first, last = nm.group(1), nm.group(2)
    if nm.group(0) in NOISE or first in NOTNAME or last in NOTNAME: return False
    ctoks = {w.lower() for w in re.findall(r"[A-Za-z]+", company)}
    if first.lower() in ctoks or last.lower() in ctoks: return False
    return True


def find_person(site, company=""):
    """Return (first, last, title, email_hint) for the most sales-relevant named person on the site's team/about pages."""
    base = re.match(r"https?://[^/]+", site).group(0); dom = base.split("//")[1].replace("www.", "")
    best = None; pattern = None
    for path in TEAM_PATHS:
        try: html = requests.get(base + path, headers=H, timeout=20).text
        except Exception: continue
        text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S); text = re.sub(r"<[^>]+>", "\n", text)
        for m in ROLE.finditer(text):
            before = text[max(0, m.start() - 80): m.start()]
            cands = [nm for nm in NAME.finditer(before) if _ok_name(nm, company)]
            if not cands:
                after = text[m.end(): m.end() + 60]
                cands = [nm for nm in NAME.finditer(after) if _ok_name(nm, company)]
                if not cands: continue
                nm = cands[0]
            else:
                nm = cands[-1]   # the name closest to (just before) the role
            score = 3 if re.search(r"sales|account|business development|territory|regional", m.group(0), re.I) else (2 if re.search(r"owner|founder|president|ceo|principal|partner", m.group(0), re.I) else 1)
            if best is None or score > best[0]: best = (score, nm.group(1), nm.group(2), m.group(0))
        # learn the address pattern from any personal email on the site (raw html: mailto: links count)
        for e in EMAIL.findall(html):
            e = e.lower()
            if not (e.endswith("@" + dom) or e.endswith("." + dom)): continue
            local = e.split("@")[0]
            if local in PREF or local in ("noreply", "no-reply", "webmaster", "careers", "jobs", "billing", "accounting", "hr"): continue
            if "." in local: pattern = "first.last"
            elif len(local) > 2: pattern = "first" if not any(ch.isdigit() for ch in local) else pattern
        time.sleep(1)
        if best and pattern: break
    if not best: return None
    _, first, last, title = best
    email = ""
    if pattern == "first.last": email = f"{first.lower()}.{last.lower()}@{dom}"
    elif pattern == "first": email = f"{first.lower()}@{dom}"
    return first, last, title, email


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
        person = find_person(site, r["company"]) if site else None
        first = person[0] if person else ""; title = person[2] if person else ""
        # prefer a named person's address when the site confirmed the pattern; else the generic inbox, addressed to the person if we found one
        addr = person[3] if (person and person[3]) else (em[0] if em else "")
        out.append({**r, "website": site, "email": addr, "contact_first": first, "contact_title": title, "status": "ready" if addr else "no-email"})
        print(r["company"], "->", site, em[:1])
        if len(out) - len(done) >= 25: break   # gentle: 25 per run
    with open("data/vendors_enriched.csv", "w", newline="") as f:
        fields = ["category", "company", "phone", "city", "website", "email", "contact_first", "contact_title", "status"]
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader()
        for row in out + [done[c] for c in done if c not in {o["company"] for o in out}]:
            w.writerow({k: row.get(k, "") for k in fields})


if __name__ == "__main__":
    main()
