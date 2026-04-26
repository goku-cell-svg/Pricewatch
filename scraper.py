"""
PriceWatch - Scraper de precios con Playwright (versión mejorada)
Simula comportamiento humano para evitar bloqueos
"""

import asyncio
import csv
import os
import json
import re
import random
from datetime import datetime
from playwright.async_api import async_playwright

# ─────────────────────────────────────────────
# LISTA DE PRODUCTOS A RASTREAR
# ─────────────────────────────────────────────
PRODUCTS = [
    {
        "name": "Brocosulf 90 caps - Nutripraxis",
        "store": "Dietética Central",
        "url": "https://www.dieteticacentral.com/marcas/nutripraxis/brocosulf-90cap.html",
        "target_price": 20.00,
    },
    # Añade más productos aquí
]

PRICE_SELECTORS = [
    "[itemprop='price']",
    ".product-price",
    ".price",
    "#price",
    ".our_price_display",
    "[class*='price']",
    "[id*='price']",
    ".product__price",
    "span.amount",
    ".current-price",
    "#our_price_display",
]

CSV_FILE = "precios.csv"
ALERTS_FILE = "alertas.json"


async def human_delay(min_ms=500, max_ms=2000):
    """Pausa aleatoria para simular comportamiento humano."""
    await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


async def get_price(page, url: str):
    """Visita la URL simulando un usuario real y extrae el precio."""
    try:
        await page.goto(url, wait_until="networkidle", timeout=45000)
        await human_delay(2000, 4000)

        # Scroll suave como haría un humano
        await page.evaluate("window.scrollTo({ top: 300, behavior: 'smooth' });")
        await human_delay(1000, 2000)

        # Intentar con selectores CSS
        for selector in PRICE_SELECTORS:
            try:
                elements = await page.query_selector_all(selector)
                for el in elements:
                    text = await el.inner_text()
                    price_str = (
                        text.strip()
                            .replace("€", "").replace("EUR", "")
                            .replace("\xa0", "").replace(" ", "")
                            .replace(",", ".")
                    )
                    match = re.search(r"\d+\.\d+", price_str)
                    if match:
                        price = float(match.group())
                        if 0.5 < price < 5000:
                            return price
            except Exception:
                continue

        # Buscar atributo content en meta precio
        try:
            meta_price = await page.get_attribute("[itemprop='price']", "content")
            if meta_price:
                price = float(meta_price.replace(",", "."))
                if 0.5 < price < 5000:
                    return price
        except Exception:
            pass

        # Buscar en HTML completo
        content = await page.content()

        # Patrón €
        matches = re.findall(r'(\d+[,\.]\d{2})\s*[€E]', content)
        if matches:
            prices = [float(m.replace(",", ".")) for m in matches if m]
            if prices:
                from collections import Counter
                return Counter(prices).most_common(1)[0][0]

        # JSON-LD
        ld_matches = re.findall(r'"price"\s*:\s*"?(\d+[.,]\d+)"?', content)
        if ld_matches:
            return float(ld_matches[0].replace(",", "."))

        return None

    except Exception as e:
        print(f"  ⚠️  Error al acceder a {url}: {e}")
        return None


def save_to_csv(results):
    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["fecha", "nombre", "tienda", "precio", "objetivo", "url"])
        if not file_exists:
            writer.writeheader()
        writer.writerows(results)


async def main():
    print("=" * 50)
    print("🔍 PriceWatch - Escaneo v2")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="es-ES",
            timezone_id="Europe/Madrid",
            extra_http_headers={
                "Accept-Language": "es-ES,es;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            }
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )

        page = await context.new_page()

        for product in PRODUCTS:
            print(f"\n📦 {product['name']}")
            print(f"   🏪 {product['store']}")

            price = await get_price(page, product["url"])

            if price:
                status = "✅" if price <= product["target_price"] else "💰"
                print(f"   {status} Precio: {price:.2f}€  (objetivo: {product['target_price']:.2f}€)")
            else:
                print(f"   ❌ No se pudo obtener el precio")

            results.append({
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "nombre": product["name"],
                "tienda": product["store"],
                "precio": price,
                "objetivo": product["target_price"],
                "url": product["url"],
            })

            await human_delay(3000, 6000)

        await browser.close()

    save_to_csv(results)
    print(f"\n💾 Guardado en {CSV_FILE}")

    alerts = [r for r in results if r["precio"] and r["precio"] <= r["objetivo"]]
    if alerts:
        print("\n🚨 ¡ALERTAS DE PRECIO!")
        for a in alerts:
            print(f"   ⬇️  {a['nombre']}: {a['precio']:.2f}€")
        with open(ALERTS_FILE, "w", encoding="utf-8") as f:
            json.dump(alerts, f, ensure_ascii=False, indent=2)
    else:
        print("\n✅ Ningún producto bajo del objetivo todavía.")

    print("\n✔️  Escaneo completado")


if __name__ == "__main__":
    asyncio.run(main())
