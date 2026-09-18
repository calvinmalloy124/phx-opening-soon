"""
Statewide Arizona liquor applications from the DLLC License Search (Google Apps Script UI).
Drives the app with Playwright, filters Status=Pending, dumps results to data/statewide_raw.json.
First version is exploratory: it logs the page structure so we can lock the selectors.
"""
import asyncio, json, os, re, sys
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://script.google.com/a/macros/azliquor.gov/s/AKfycbxt14jd49w9bJBu9s4qYFJIh9nq0cgHX2WJCTSmlhbYTPGlOJZhn5bIFSB_MOD-ELMgpA/exec?origin=https%3A%2F%2Fliquor.az.gov"
OUT = Path("data/statewide_raw.json")


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1400, "height": 1000})
        await pg.goto(URL, wait_until="networkidle", timeout=90000)
        await pg.wait_for_timeout(4000)
        # the app renders inside nested iframes (sandboxFrame -> userHtmlFrame)
        frame = None
        for f in pg.frames:
            try:
                if await f.locator("select").count() > 0: frame = f; break
            except Exception: pass
        if frame is None:
            print("no frame with selects; frames:", [f.url[:80] for f in pg.frames]); await b.close(); return
        sels = await frame.locator("select").all()
        info = []
        for s in sels:
            opts = await s.locator("option").all_inner_texts()
            info.append({"id": await s.get_attribute("id"), "name": await s.get_attribute("name"), "options": opts[:60]})
        print("SELECTS:", json.dumps(info)[:3000])
        # choose Status=Pending, County=Maricopa if present
        for s, want in zip(sels, [None]*len(sels)):
            pass
        for s in sels:
            opts = await s.locator("option").all_inner_texts()
            if any(o.strip().lower() == "pending" for o in opts):
                await s.select_option(label=[o for o in opts if o.strip().lower() == "pending"][0])
            if any("maricopa" in o.lower() for o in opts):
                await s.select_option(label=[o for o in opts if "maricopa" in o.lower()][0])
        btn = frame.get_by_role("button", name=re.compile("search", re.I))
        await btn.first.click()
        await pg.wait_for_timeout(8000)
        # grab any tables / result rows
        tables = await frame.locator("table").all()
        rows = []
        for t in tables:
            for tr in await t.locator("tr").all():
                cells = await tr.locator("th,td").all_inner_texts()
                if cells: rows.append([c.strip() for c in cells])
        print(f"TABLES: {len(tables)} ROWS: {len(rows)}")
        for r in rows[:15]: print("  ", r)
        if not rows:
            txt = await frame.locator("body").inner_text()
            print("BODY TEXT:", txt[:2500])
        OUT.parent.mkdir(exist_ok=True); OUT.write_text(json.dumps(rows, indent=1))
        await b.close()

asyncio.run(main())
