"""Script de diagnóstico - muestra el HTML que ve el scraper"""
import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="es-ES",
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )
        page = await context.new_page()
        print("Visitando la web...")
        await page.goto(
            "https://www.dieteticacentral.com/marcas/nutripraxis/brocosulf-90cap.html",
            wait_until="networkidle",
            timeout=45000
        )
        await asyncio.sleep(4)
        content = await page.content()
        print("=== HTML RECIBIDO (primeros 4000 caracteres) ===")
        print(content[:4000])
        print("=== FIN ===")
        await browser.close()

asyncio.run(test())
