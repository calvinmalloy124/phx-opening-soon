"""
Enrich active filings with public contact signals. Cached in data/enrich.json (one lookup per record).
- Phoenix: parse the application PDF for applicant/agent name and phone.
- All: DuckDuckGo HTML search for the venue's Instagram and website.
Fields added to filings: agent (if missing), phone, instagram, website.
"""
import io, json, os, re, time, html
from pathlib import Path
import requests

ROOT = Path(__file__).parent
FIL = ROOT / "data" / "filings.json"; CACHE = ROOT / "data" / "enrich.json"
H = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
PHONE = re.compile(r"\(?\b\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b")
SKIP = ("yelp.", "facebook.", "instagram.", "tripadvisor.", "doordash.", "ubereats.", "grubhub.", "opentable.", "google.", "mapquest.", "phoenix.gov", "scottsdaleaz.gov", "legistar.", "azliquor", "restaurantji", "menupix", "zomato", "foursquare", "loopnet", "crexi", "bizbuysell", "linkedin.")
MAX_PER_RUN = 3


def ocr_pdf(b, pages=2):
    """Scanned PDF -> text via tesseract (installed in the workflow)."""
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
        imgs = convert_from_bytes(b, dpi=200, first_page=1, last_page=pages)
        return "\n".join(pytesseract.image_to_string(im) for im in imgs)
    except Exception as ex:
        print(f"  ocr error {ex}"); return ""


def phoenix_pdf(url):
    try:
        from pypdf import PdfReader
        r = requests.get(url, headers=H, timeout=60)
        b = r.content
        txt = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(b)).pages[:3])
        if len(txt.strip()) < 50:
            txt = ocr_pdf(b)
        print(f"  pdf {r.status_code} {len(b)}B text={len(txt)}")
        if os.environ.get("DUMP_OCR"): print("----OCR----\n" + txt[:3000] + "\n----END----")
    except Exception as ex:
        print(f"  pdf error {ex}")
        return {}
    out = {}
    m = PHONE.search(txt)
    if m: out["phone"] = m.group(0)
    for pat in [r"(?:Agent|Applicant|Owner|Controlling Person)[^\n:]{0,40}[:\-]\s*([A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){1,3})",
                r"(?:Agent|Applicant)[^\n]*\n\s*([A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){1,3})",
                r"Name of Applicant[^\n]*\n\s*([A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){1,3})"]:
        m = re.search(pat, txt)
        if m: out["agent"] = m.group(1).strip(); break
    return out


BRAVE = os.environ.get("BRAVE_KEY", "")

def brave(q):
    r = requests.get("https://api.search.brave.com/res/v1/web/search", params={"q": q, "count": 8, "country": "us"},
                     headers={"Accept": "application/json", "X-Subscription-Token": BRAVE}, timeout=30)
    if r.status_code != 200: print(f"  brave {r.status_code}"); return []
    return [x.get("url") for x in r.json().get("web", {}).get("results", []) if x.get("url")]


def ddg(q):
    if BRAVE: return brave(q)
    try:
        r = requests.post("https://html.duckduckgo.com/html/", data={"q": q}, headers=H, timeout=30)
        links = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"', r.text)
        if not links:
            print(f"  ddg {r.status_code} no results ({len(r.text)}B) -> trying bing")
            b = requests.get("https://www.bing.com/search", params={"q": q, "setlang": "en"}, headers=H, timeout=30)
            links = re.findall(r'<li class="b_algo".*?<h2><a href="([^"]+)"', b.text, re.S)
            print(f"  bing {b.status_code} {len(links)} links")
        return links
    except Exception as ex:
        print(f"  search error {ex}")
        return []


def clean(u):
    m = re.search(r"uddg=([^&]+)", u)
    return requests.utils.unquote(m.group(1)) if m else u


def socials(name, city):
    out = {}
    for u in ddg(f'"{name}" {city} instagram')[:8]:
        u = clean(u)
        if "instagram.com/" in u and "/p/" not in u and "/reel/" not in u and "/explore/" not in u:
            out["instagram"] = u.split("?")[0]; break
    time.sleep(2)
    for u in ddg(f'"{name}" {city} restaurant')[:8]:
        u = clean(u)
        if u.startswith("http") and not any(s in u for s in SKIP):
            out["website"] = u.split("?")[0]; break
    time.sleep(2)
    return out


def main():
    filings = json.loads(FIL.read_text()) if FIL.exists() else {}
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    todo = [k for k, v in filings.items() if v.get("active") and k not in cache and v.get("category") not in ("beer_wine_store", "liquor_store", "other")]
    done = 0
    for k in todo[:MAX_PER_RUN]:
        v = filings[k]; e = {}
        if v.get("city") == "Phoenix" and v.get("pdf_application"):
            e.update(phoenix_pdf(v["pdf_application"]))
        e.update(socials(v["name"], v.get("city", "Phoenix")))
        print(f"{v['name']} ({v.get('city')}) -> {e}")
        if e: cache[k] = e
        done += 1
    # merge cached fields into filings (never overwrite a non-empty agent)
    for k, e in cache.items():
        if k in filings:
            for f, val in e.items():
                if f == "agent" and filings[k].get("agent"): continue
                if val: filings[k][f] = val
    CACHE.write_text(json.dumps(cache, indent=1))
    FIL.write_text(json.dumps(filings, indent=1))
    print(f"enriched {done} new, {len(todo) - done} remaining, cache {len(cache)}")


if __name__ == "__main__":
    main()
