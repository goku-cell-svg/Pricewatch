"""
PriceWatch - Scraper de precios via API JSON
Más fiable que el scraping tradicional, sin bloqueos
"""

import csv
import os
import json
import re
import urllib.request
import urllib.error
from datetime import datetime

# ─────────────────────────────────────────────
# LISTA DE PRODUCTOS A RASTREAR
# ─────────────────────────────────────────────
PRODUCTS = [
    {
        "name": "Brocosulf 90 caps - Nutripraxis",
        "store": "Herbolario Saludnatural",
        "url_display": "https://www.herbolariosaludnatural.com/products/18108-brocosulf-nutripraxis-90-capsulas",
        # URL de la API JSON de Shopify (añadir .json al slug del producto)
        "url_api": "https://www.herbolariosaludnatural.com/products/18108-brocosulf-nutripraxis-90-capsulas.json",
        "type": "shopify",
        "target_price": 75.00,  # Cambia este valor a tu precio objetivo
    },
    # ── Cómo añadir más productos de tiendas Shopify ──
    # Busca el producto en la tienda, copia la URL y añade .json al final
    # {
    #     "name": "Nombre del producto",
    #     "store": "Nombre tienda",
    #     "url_display": "https://tienda.com/products/nombre-producto",
    #     "url_api": "https://tienda.com/products/nombre-producto.json",
    #     "type": "shopify",
    #     "target_price": 25.00,
    # },
]

CSV_FILE = "precios.csv"
ALERTS_FILE = "alertas.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def get_price_shopify(url: str):
    """Obtiene el precio desde la API JSON de Shopify."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
            variants = data.get("product", {}).get("variants", [])
            if variants:
                price = float(variants[0]["price"])
                return price
    except Exception as e:
        print(f"  ⚠️  Error: {e}")
    return None


def get_price_html(url: str):
    """Obtiene el precio buscando patrones en el HTML (para tiendas sin API)."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read().decode("utf-8", errors="ignore")

        # Buscar en JSON-LD
        ld_matches = re.findall(r'"price"\s*:\s*"?(\d+[.,]\d+)"?', content)
        if ld_matches:
            return float(ld_matches[0].replace(",", "."))

        # Buscar patrón €
        matches = re.findall(r'(\d+[,\.]\d{2})\s*€', content)
        if matches:
            from collections import Counter
            prices = [float(m.replace(",", ".")) for m in matches]
            return Counter(prices).most_common(1)[0][0]

    except Exception as e:
        print(f"  ⚠️  Error: {e}")
    return None


def save_to_csv(results: list):
    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["fecha", "nombre", "tienda", "precio", "objetivo", "url"])
        if not file_exists:
            writer.writeheader()
        writer.writerows(results)


def main():
    print("=" * 50)
    print("🔍 PriceWatch - Escaneo via API JSON")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    results = []

    for product in PRODUCTS:
        print(f"\n📦 {product['name']}")
        print(f"   🏪 {product['store']}")

        if product.get("type") == "shopify":
            price = get_price_shopify(product["url_api"])
        else:
            price = get_price_html(product["url_display"])

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
            "url": product["url_display"],
        })

    save_to_csv(results)
    print(f"\n💾 Guardado en {CSV_FILE}")

    alerts = [r for r in results if r["precio"] and r["precio"] <= r["objetivo"]]
    if alerts:
        print("\n🚨 ¡ALERTAS DE PRECIO!")
        for a in alerts:
            print(f"   ⬇️  {a['nombre']}: {a['precio']:.2f}€ (objetivo: {a['objetivo']:.2f}€)")
        with open(ALERTS_FILE, "w", encoding="utf-8") as f:
            json.dump(alerts, f, ensure_ascii=False, indent=2)
    else:
        print("\n✅ Ningún producto bajo del objetivo todavía.")

    print("\n✔️  Escaneo completado")


if __name__ == "__main__":
    main()
