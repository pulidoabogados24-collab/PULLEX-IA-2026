import sys, asyncio
from playwright.async_api import async_playwright
async def main(html, out, w, h, scale=1, pdf=None, transparent=False):
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": int(w), "height": int(h)}, device_scale_factor=float(scale))
        await pg.goto("file://" + html)
        await pg.evaluate("document.fonts.ready")
        await pg.wait_for_timeout(400)
        await pg.screenshot(path=out, omit_background=transparent, full_page=False)
        if pdf:
            await pg.pdf(path=pdf, width=f"{w}px", height=f"{h}px", print_background=True)
        await b.close()
a = sys.argv
asyncio.run(main(a[1], a[2], a[3], a[4], a[5] if len(a) > 5 else 1, a[6] if len(a) > 6 and a[6] != "-" else None, len(a) > 7 and a[7] == "t"))
