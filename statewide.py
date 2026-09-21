"""Download the statewide Pending Applications CSV from the DLLC License Search (Apps Script UI) with Playwright."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://script.google.com/a/macros/azliquor.gov/s/AKfycbxt14jd49w9bJBu9s4qYFJIh9nq0cgHX2WJCTSmlhbYTPGlOJZhn5bIFSB_MOD-ELMgpA/exec?origin=https%3A%2F%2Fliquor.az.gov"
OUT = Path("data/statewide_pending.csv")


async def app_frame(pg):
    for _ in range(30):
        for f in pg.frames:
            try:
                if await f.locator("select").count() > 0: return f
            except Exception: pass
        await pg.wait_for_timeout(1000)
    return None


async def click_label(frame, label):
    for b in await frame.locator("button, input[type=button], a").all():
        try:
            t = ((await b.inner_text()) if await b.evaluate("e=>e.tagName") != "INPUT" else (await b.get_attribute("value")) or "").strip()
        except Exception: continue
        if t.split("\n")[0].strip().lower() == label.lower():
            await b.click(); return True
    return False


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(accept_downloads=True, viewport={"width": 1400, "height": 1000})
        pg = await ctx.new_page()
        await pg.goto(URL, wait_until="networkidle", timeout=90000)
        frame = await app_frame(pg)
        if frame is None: raise SystemExit("no app frame")
        await click_label(frame, "Specialized Reports"); await pg.wait_for_timeout(1500)
        if not await click_label(frame, "Pending Applications"): raise SystemExit("no Pending Applications button")
        for _ in range(40):
            await pg.wait_for_timeout(1000)
            if await frame.locator("table").count() > 0: break
        async with pg.expect_download(timeout=60000) as dl:
            await click_label(frame, "Export to CSV")
        d = await dl.value
        OUT.parent.mkdir(exist_ok=True); await d.save_as(str(OUT))
        n = sum(1 for _ in OUT.open()) - 1
        print(f"statewide pending csv: {OUT.stat().st_size} bytes, ~{n} rows")
        await b.close()

asyncio.run(main())
