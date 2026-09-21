"""
Statewide Arizona newly-issued liquor licenses from the DLLC License Search (Google Apps Script UI).
Drives the app with Playwright: Status=Active, issued in the last N days, restaurant/bar-type licenses.
Writes data/statewide_raw.json (rows) and logs structure for parser tuning.
"""
import asyncio, json, os, re, sys
from datetime import date, timedelta
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://script.google.com/a/macros/azliquor.gov/s/AKfycbxt14jd49w9bJBu9s4qYFJIh9nq0cgHX2WJCTSmlhbYTPGlOJZhn5bIFSB_MOD-ELMgpA/exec?origin=https%3A%2F%2Fliquor.az.gov"
OUT = Path("data/statewide_raw.json")
DAYS = int(os.environ.get("DAYS", "30"))
TYPES = ["012", "006", "007", "011", "019", "003"]   # restaurant, bar, beer&wine bar, hotel, tasting room, microbrewery


async def app_frame(pg):
    for _ in range(20):
        for f in pg.frames:
            try:
                if await f.locator("select").count() > 0: return f
            except Exception: pass
        await pg.wait_for_timeout(1000)
    return None


async def pick(frame, sel, pred):
    opts = await sel.locator("option").all_inner_texts()
    for o in opts:
        if pred(o): await sel.select_option(label=o); return o
    return None


async def run_one(frame, pg, typ):
    sels = await frame.locator("select").all()
    chosen = {}
    for s in sels:
        opts = await s.locator("option").all_inner_texts()
        joined = " | ".join(opts).lower()
        if "active" in joined and "expired" in joined:
            chosen["status"] = await pick(frame, s, lambda o: o.strip().lower() == "active")
        elif any(o.strip().startswith(typ) for o in opts):
            chosen["type"] = await pick(frame, s, lambda o: o.strip().startswith(typ))
    # issue date range: try common input ids/labels
    start = (date.today() - timedelta(days=DAYS)).strftime("%m/%d/%Y")
    inputs = await frame.locator("input").all()
    names = []
    for i in inputs:
        nm = (await i.get_attribute("id") or "") + "|" + (await i.get_attribute("name") or "") + "|" + (await i.get_attribute("placeholder") or "") + "|" + (await i.get_attribute("type") or "")
        names.append(nm)
        if re.search(r"issue|issued|start|from", nm, re.I) and not re.search(r"end|to\b", nm, re.I):
            try:
                await i.fill(start if "date" not in nm.lower().split("|")[-1] else (date.today() - timedelta(days=DAYS)).isoformat())
                chosen["issued_start"] = start
            except Exception as ex: chosen["issued_start_err"] = str(ex)[:80]
    print("INPUTS:", names[:20])
    print("CHOSEN:", chosen)
    btns = await frame.locator("button, input[type=button], input[type=submit]").all()
    labels = []
    for b in btns:
        labels.append(((await b.inner_text()) or (await b.get_attribute("value")) or "").strip())
    print("BUTTONS:", labels)
    async def do_search():
        target = None
        for b, l in zip(btns, labels):
            if re.search(r"search", l, re.I) and not re.search(r"clear|reset", l, re.I): target = b; break
        if target is None: target = btns[0]
        await target.click()
        for _ in range(30):   # up to 30s for results
            await pg.wait_for_timeout(1000)
            if await frame.locator("table").count() > 0 or await frame.locator("text=/result|found|records|no .*match/i").count() > 0: break
        rows = []
        for t in await frame.locator("table").all():
            for tr in await t.locator("tr").all():
                cells = await tr.locator("th,td").all_inner_texts()
                if cells: rows.append([c.strip() for c in cells])
        return rows
    rows = await do_search()
    if not rows:
        print("no rows with date filter; retrying without dates")
        for i in await frame.locator("input").all():
            nm = (await i.get_attribute("id") or "")
            if nm in ("startDate", "endDate"): await i.fill("")
        rows = await do_search()
    print(f"TYPE {typ}: tables={await frame.locator('table').count()} rows={len(rows)}")
    for r in rows[:8]: print("  ", r)
    txt = await frame.locator("body").inner_text()
    i = txt.find("Search Filters"); j = txt.find("020 -")
    print("BODY-HEAD:", txt[:600].replace("\n", " | "))
    print("BODY-AFTER-FILTERS:", txt[j+6: j+2500].replace("\n", " | ") if j >= 0 else txt[-2500:])
    return rows


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1400, "height": 1000})
        await pg.goto(URL, wait_until="networkidle", timeout=90000)
        frame = await app_frame(pg)
        if frame is None: print("no app frame"); await b.close(); return
        allrows = {}
        for typ in TYPES[: int(os.environ.get("MAX_TYPES", "2"))]:
            try:
                allrows[typ] = await run_one(frame, pg, typ)
            except Exception as ex:
                print(f"TYPE {typ} error: {ex}")
            await pg.goto(URL, wait_until="networkidle", timeout=90000)
            frame = await app_frame(pg)
        OUT.parent.mkdir(exist_ok=True); OUT.write_text(json.dumps(allrows, indent=1))
        await b.close()

asyncio.run(main())
