"""
Statewide Arizona liquor data from the DLLC License Search (Google Apps Script UI), via Playwright.
Mode "pending": open Specialized Reports -> Pending Applications, dump the table, try Export to CSV.
"""
import asyncio, json, os, re
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://script.google.com/a/macros/azliquor.gov/s/AKfycbxt14jd49w9bJBu9s4qYFJIh9nq0cgHX2WJCTSmlhbYTPGlOJZhn5bIFSB_MOD-ELMgpA/exec?origin=https%3A%2F%2Fliquor.az.gov"
Path("data").mkdir(exist_ok=True)


async def app_frame(pg):
    for _ in range(25):
        for f in pg.frames:
            try:
                if await f.locator("select").count() > 0: return f
            except Exception: pass
        await pg.wait_for_timeout(1000)
    return None


async def click_label(frame, label):
    for b in await frame.locator("button, input[type=button], a").all():
        t = ((await b.inner_text()) if await b.evaluate("e=>e.tagName") != "INPUT" else (await b.get_attribute("value")) or "").strip()
        if t.split("\n")[0].strip().lower() == label.lower():
            await b.click(); return True
    return False


async def dump_tables(frame):
    rows = []
    for t in await frame.locator("table").all():
        for tr in await t.locator("tr").all():
            cells = await tr.locator("th,td").all_inner_texts()
            if cells: rows.append([c.strip() for c in cells])
    return rows


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(accept_downloads=True, viewport={"width": 1400, "height": 1000})
        pg = await ctx.new_page()
        await pg.goto(URL, wait_until="networkidle", timeout=90000)
        frame = await app_frame(pg)
        if frame is None: print("no app frame"); await b.close(); return
        # open the Specialized Reports menu, then Pending Applications
        opened = await click_label(frame, "Specialized Reports")
        await pg.wait_for_timeout(1500)
        ok = await click_label(frame, "Pending Applications")
        print("menu:", opened, "pending clicked:", ok)
        rows = []
        for _ in range(40):
            await pg.wait_for_timeout(1000)
            rows = await dump_tables(frame)
            if rows: break
        print(f"PENDING rows={len(rows)}")
        for r in rows[:12]: print("  ", r)
        txt = await frame.locator("body").inner_text()
        k = txt.find("Pending Applications")
        print("BODY:", txt[k: k + 3000].replace("\n", " | ") if k >= 0 else txt[-3000:].replace("\n", " | "))
        Path("data/statewide_raw.json").write_text(json.dumps(rows, indent=1))
        # try CSV export
        try:
            async with pg.expect_download(timeout=30000) as dl:
                await click_label(frame, "Export to CSV")
            d = await dl.value
            await d.save_as("data/statewide_pending.csv")
            print("CSV saved:", d.suggested_filename, Path("data/statewide_pending.csv").stat().st_size, "bytes")
            print(Path("data/statewide_pending.csv").read_text()[:1500])
        except Exception as ex:
            print("csv export:", str(ex)[:120])
        await b.close()

asyncio.run(main())
