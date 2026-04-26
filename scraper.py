"""
PriceWatch - Scraper con notificaciones Telegram
"""

import csv
import os
import json
import re
import urllib.request
from datetime import datetime
from collections import Counter

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")

PRODUCTS_FILE = "productos.json"
CSV_FILE = "precios.csv"
ALERTS_FILE = "alertas.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/html",
}

# Productos por defecto si no existe productos.json
DEFAULT_PRODUCTS = [
    {
        "name": "Brocosulf 90 caps - Nutripraxis",
        "store": "Herbolario Saludnatural",
        "url": "https://www.herbolariosaludnatural.com/products/18108-brocosulf-nutripraxis-90-capsulas",
        "target_price": 75.00,
    },
]


def send_telegram(text):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Error Telegram: {e}")


def load_products():
    if os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    # Primera vez: guardar los productos por defecto
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_PRODUCTS, f, ensure_ascii=False, indent=2)
    return DEFAULT_PRODUCTS


def get_price_shopify(url):
    try:
        api_url = url.rstrip("/") + ".json"
        req = urllib.request.Request(api_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
            variants = data.get("product", {}).get("variants", [])
            if variants:
                return float(variants[0]["price"])
    except Exception:
        pass
    return None


def get_price_html(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as r:
            content = r.read().decode("utf-8", errors="ignore")
        ld = re.findall(r'"price"\s*:\s*"?(\d+[.,]\d+)"?', content)
        if ld:
            return float(ld[0].replace(",", "."))
        matches = re.findall(r'(\d+[,\.]\d{2})\s*[€E]', content)
        if matches:
            prices = [float(m.replace(",", ".")) for m in matches]
            return Counter(prices).most_common(1)[0][0]
    except Exception:
        pass
    return None


def get_price(product):
    price = get_price_shopify(product["url"])
    if price:
        return price
    return get_price_html(product["url"])


def main():
    print("=" * 50)
    print("🔍 PriceWatch - Escaneo diario")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    products = load_products()
    results = []
    alerts = []

    for p in products:
        print(f"\n📦 {p['name']} — {p['store']}")
        price = get_price(p)
        if price:
            icon = "✅" if price <= p["target_price"] else "💰"
            print(f"   {icon} {price:.2f}€ (objetivo: {p['target_price']:.2f}€)")
        else:
            print(f"   ❌ No encontrado")

        result = {
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "nombre": p["name"],
            "tienda": p["store"],
            "precio": price,
            "objetivo": p["target_price"],
            "url": p["url"],
        }
        results.append(result)
        if price and price <= p["target_price"]:
            alerts.append(result)

    # Guardar CSV
    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["fecha", "nombre", "tienda", "precio", "objetivo", "url"])
        if not file_exists:
            writer.writeheader()
        writer.writerows(results)
    print(f"\n💾 Guardado en {CSV_FILE}")

    # Enviar resumen diario por Telegram
    lines = [f"📊 <b>Resumen diario — {datetime.now().strftime('%d/%m/%Y')}</b>\n"]
    for r in results:
        if r["precio"]:
            icon = "✅" if r["precio"] <= r["objetivo"] else "💰"
            lines.append(f"{icon} <b>{r['nombre']}</b>")
            lines.append(f"   {r['precio']:.2f}€  (obj: {r['objetivo']:.2f}€)")
            lines.append(f"   🏪 {r['tienda']}\n")
        else:
            lines.append(f"❌ <b>{r['nombre']}</b> — precio no encontrado\n")

    if alerts:
        lines.append("🚨 <b>¡PRECIO OBJETIVO ALCANZADO!</b>")
        for a in alerts:
            lines.append(f"⬇️ {a['nombre']}: {a['precio']:.2f}€")
        with open(ALERTS_FILE, "w", encoding="utf-8") as f:
            json.dump(alerts, f, ensure_ascii=False, indent=2)

    send_telegram("\n".join(lines))
    print("📱 Resumen enviado por Telegram")
    print("\n✔️  Escaneo completado")


if __name__ == "__main__":
    main()
