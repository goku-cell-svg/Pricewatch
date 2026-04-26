"""
PriceWatch Bot de Telegram
Gestiona productos y envia alertas de precio
"""

import json
import os
import csv
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


# ── TELEGRAM ──────────────────────────────────

def send_message(text, chat_id=None):
    cid = chat_id or CHAT_ID
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = json.dumps({"chat_id": cid, "text": text, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Error Telegram: {e}")


def get_updates(offset=0):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={offset}&timeout=5"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception:
        return {"result": []}


# ── PRODUCTOS ─────────────────────────────────

def load_products():
    if not os.path.exists(PRODUCTS_FILE):
        return []
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_products(products):
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)


# ── SCRAPING ──────────────────────────────────

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


def get_product_name(url):
    """Intenta obtener el nombre del producto desde la URL de Shopify."""
    try:
        api_url = url.rstrip("/") + ".json"
        req = urllib.request.Request(api_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
            return data.get("product", {}).get("title", "")
    except Exception:
        pass
    # Fallback: extraer nombre de la URL
    slug = url.rstrip("/").split("/")[-1]
    return slug.replace("-", " ").title()


def get_store_name(url):
    """Extrae el nombre de la tienda de la URL."""
    match = re.search(r'https?://(?:www\.)?([^/]+)', url)
    if match:
        domain = match.group(1)
        return domain.split(".")[0].capitalize()
    return "Tienda"


# ── ESCANEO COMPLETO ──────────────────────────

def scan_all():
    products = load_products()
    if not products:
        return [], []

    results = []
    alerts = []

    for p in products:
        price = get_price(p)
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

    if alerts:
        with open(ALERTS_FILE, "w", encoding="utf-8") as f:
            json.dump(alerts, f, ensure_ascii=False, indent=2)

    return results, alerts


# ── COMANDOS ──────────────────────────────────

def cmd_ayuda():
    return (
        "🤖 <b>PriceWatch Bot</b>\n\n"
        "Comandos:\n\n"
        "/lista — Ver tus productos\n"
        "/precios — Escanear precios ahora\n"
        "/añadir [url] [precio objetivo] — Añadir producto\n"
        "  Ejemplo:\n"
        "  /añadir https://tienda.com/producto 75\n"
        "/borrar [número] — Borrar un producto\n"
        "/ayuda — Ver esta ayuda"
    )


def cmd_lista():
    products = load_products()
    if not products:
        return "📭 Sin productos. Usa /añadir [url] [precio] para empezar."
    lines = ["📋 <b>Tus productos:</b>\n"]
    for i, p in enumerate(products, 1):
        lines.append(f"<b>{i}. {p['name']}</b>")
        lines.append(f"   🏪 {p['store']}")
        lines.append(f"   🎯 Objetivo: {p['target_price']}€\n")
    return "\n".join(lines)


def cmd_precios():
    products = load_products()
    if not products:
        return "📭 Sin productos. Usa /añadir [url] [precio] para empezar."
    send_message("⏳ Escaneando precios...")
    results, alerts = scan_all()
    lines = [f"📊 <b>Precios — {datetime.now().strftime('%d/%m %H:%M')}</b>\n"]
    for r in results:
        if r["precio"]:
            icon = "✅" if r["precio"] <= r["objetivo"] else "💰"
            lines.append(f"{icon} <b>{r['nombre']}</b>")
            lines.append(f"   {r['precio']:.2f}€  (obj: {r['objetivo']:.2f}€)")
            lines.append(f"   🏪 {r['tienda']}\n")
        else:
            lines.append(f"❌ <b>{r['nombre']}</b> — no encontrado\n")
    if alerts:
        lines.append("🚨 <b>¡Precio objetivo alcanzado!</b>")
    return "\n".join(lines)


def cmd_añadir(args):
    parts = args.strip().split()
    if len(parts) < 2:
        return "❌ Formato: /añadir [url] [precio]\nEjemplo: /añadir https://tienda.com/producto 75"
    url = parts[0]
    try:
        target = float(parts[1].replace(",", ".").replace("€", ""))
    except ValueError:
        return "❌ El precio debe ser un número. Ejemplo: /añadir https://... 75"

    if not url.startswith("http"):
        return "❌ La URL debe empezar por https://"

    send_message("🔍 Obteniendo información del producto...")
    name = get_product_name(url)
    store = get_store_name(url)

    products = load_products()
    products.append({
        "name": name,
        "store": store,
        "url": url,
        "target_price": target,
        "added": datetime.now().strftime("%Y-%m-%d"),
    })
    save_products(products)

    return (
        f"✅ <b>Producto añadido</b>\n\n"
        f"📦 {name}\n"
        f"🏪 {store}\n"
        f"🎯 Objetivo: {target}€"
    )


def cmd_borrar(args):
    try:
        idx = int(args.strip()) - 1
    except ValueError:
        return "❌ Indica el número del producto. Usa /lista para ver los números."
    products = load_products()
    if idx < 0 or idx >= len(products):
        return "❌ Número fuera de rango. Usa /lista para ver los productos."
    removed = products.pop(idx)
    save_products(products)
    return f"🗑️ Eliminado: <b>{removed['name']}</b>"


# ── BUCLE PRINCIPAL ───────────────────────────

def process_message(text, chat_id):
    text = text.strip()
    lower = text.lower()

    if lower in ["/start", "/ayuda", "/help"]:
        send_message(cmd_ayuda(), chat_id)
    elif lower == "/lista":
        send_message(cmd_lista(), chat_id)
    elif lower == "/precios":
        send_message(cmd_precios(), chat_id)
    elif lower.startswith("/añadir") or lower.startswith("/anadir"):
        args = text.split(maxsplit=1)[1] if len(text.split()) > 1 else ""
        send_message(cmd_añadir(args), chat_id)
    elif lower.startswith("/borrar"):
        args = text.split(maxsplit=1)[1] if len(text.split()) > 1 else ""
        send_message(cmd_borrar(args), chat_id)
    else:
        send_message("No entiendo ese comando. Usa /ayuda para ver los comandos disponibles.", chat_id)


def main():
    print("🤖 PriceWatch Bot iniciado")
    send_message("🚀 <b>PriceWatch Bot</b> iniciado y listo.\nUsa /ayuda para ver los comandos.")
    offset = 0
    while True:
        updates = get_updates(offset)
        for update in updates.get("result", []):
            offset = update["update_id"] + 1
            msg = update.get("message", {})
            text = msg.get("text", "")
            chat_id = str(msg.get("chat", {}).get("id", ""))
            if text and chat_id:
                print(f"Mensaje de {chat_id}: {text}")
                process_message(text, chat_id)
        import time
        time.sleep(2)


if __name__ == "__main__":
    main()
