"""
PriceWatch - Scraper de precios con Playwright
Extrae precios de una lista de productos y los guarda en precios.csv
"""

import asyncio
import csv
import os
import json
from datetime import datetime
from playwright.async_api import async_playwright

# ─────────────────────────────────────────────
# LISTA DE PRODUCTOS A RASTREAR
# Añade o quita productos aquí
# ─────────────────────────────────────────────
PRODUCTS = [
    {
        "name": "Brocosulf 90 caps - Nutripraxis",
        "store": "Dietética Central",
        "url": "https://www.dieteticacentral.com/marcas/nutripraxis/brocosulf-90cap.html",
        "target_price": 20.00,  # Cambia este valor al precio que consideres objetivo
    },
    # Añade más productos así:
    # {
    #     "name": "Nombre del producto",
    #     "store": "Nombre de la tienda",
    #     "url": "https://...",
    #     "target_price": 25.00,
    # },
]

# ─────────────────────────────────────────────
# SELECTORES CSS PARA ENCONTRAR EL PRECIO
# Intentamos varios selectores comunes de tiendas
# ─────────────────────────────────────────────
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
]

CSV_FILE = "precios.csv"
ALERTS_FILE = "alertas.json"


async def get_price(page, url: str) -> float | None:
    """Visita la URL y extrae el precio usando múltiples selectores."""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)  # Espera a que cargue el JS

        for selector in PRICE_SELECTORS:
            try:
                elements = await page.query_selector_all(selector)
                for el in elements:
                    text = await el.inner_text()
                    text = text.strip()
                    # Limpiamos el texto para extraer el número
                    price_str = (
                        text.replace("€", "")
                            .replace("EUR", "")
                            .replace("\xa0", "")
                            .replace(" ", "")
                            .replace(",", ".")
                            .strip()
                    )
                    # Nos quedamos solo con el primer número válido
                    import re
                    match = re.search(r"\d+\.\d+", price_str)
                    if match:
                        price = float(match.group())
                        if 0.5 < price < 5000:  # Rango razonable de precios
                            return price
            except Exception:
                continue

        # Último recurso: buscar patrón de precio en el HTML completo
        import re
        content = await page.content()
        matches = re.findall(r'(\d+[,\.]\d{2})\s*€', content)
        if matches:
            prices = []
            for m in matches:
                try:
                    prices.append(float(m.replace(",", ".")))
                except Exception:
                    pass
            if prices:
                # Devolvemos el precio más frecuente (suele ser el del producto)
                from collections import Counter
                return Counter(prices).most_common(1)[0][0]

        return None

    except Exception as e:
        print(f"  ⚠️  Error al acceder a {url}: {e}")
        return None


def save_to_csv(results: list):
    """Guarda los resultados en el archivo CSV."""
    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["fecha", "nombre", "tienda", "precio", "objetivo", "url"])
        if not file_exists:
            writer.writeheader()
        writer.writerows(results)


def check_alerts(results: list) -> list:
    """Devuelve productos que están por debajo del precio objetivo."""
    alerts = []
    for r in results:
        if r["precio"] and r["precio"] <= r["objetivo"]:
            alerts.append(r)
    return alerts


async def main():
    print("=" * 50)
    print("🔍 PriceWatch - Inicio del escaneo")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        for product in PRODUCTS:
            print(f"\n📦 {product['name']}")
            print(f"   🏪 {product['store']}")
            print(f"   🔗 {product['url']}")

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

        await browser.close()

    # Guardar resultados
    save_to_csv(results)
    print(f"\n💾 Resultados guardados en {CSV_FILE}")

    # Comprobar alertas
    alerts = check_alerts(results)
    if alerts:
        print("\n🚨 ¡ALERTAS DE PRECIO!")
        for a in alerts:
            print(f"   ⬇️  {a['nombre']}: {a['precio']:.2f}€ (objetivo: {a['objetivo']:.2f}€)")
        with open(ALERTS_FILE, "w", encoding="utf-8") as f:
            json.dump(alerts, f, ensure_ascii=False, indent=2)
    else:
        print("\n✅ Ningún producto ha bajado del precio objetivo todavía.")

    print("\n" + "=" * 50)
    print("✔️  Escaneo completado")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
