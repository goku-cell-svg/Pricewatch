# 📡 PriceWatch — Seguimiento de precios automático

Escanea precios de productos en tiendas online automáticamente cada día y guarda el historial.

---

## 📁 Archivos del proyecto

| Archivo | Para qué sirve |
|---|---|
| `scraper.py` | El script que extrae los precios |
| `.github/workflows/pricewatch.yml` | Le dice a GitHub cuándo y cómo ejecutarlo |
| `precios.csv` | Histórico de todos los precios (se crea automáticamente) |
| `alertas.json` | Productos que bajaron del precio objetivo (se crea automáticamente) |

---

## ➕ Cómo añadir un nuevo producto

Abre el archivo `scraper.py` y busca la sección `PRODUCTS`. Añade un bloque como este:

```python
{
    "name": "Nombre del producto",
    "store": "Nombre de la tienda",
    "url": "https://www.tienda.com/producto",
    "target_price": 25.00,
},
```

---

## ▶️ Cómo ejecutarlo manualmente

1. Ve a tu repositorio en GitHub
2. Pulsa la pestaña **Actions**
3. Selecciona **PriceWatch - Escaneo diario de precios**
4. Pulsa **Run workflow** → **Run workflow**

---

## 🕘 Ejecución automática

El scraper se ejecuta automáticamente todos los días a las **9:00 hora de España**.
Los resultados se guardan en `precios.csv` dentro del propio repositorio.

---

## 📊 Ver el histórico de precios

Abre el archivo `precios.csv` desde GitHub. Contiene columnas:
- `fecha` — cuándo se registró
- `nombre` — nombre del producto
- `tienda` — tienda donde se comprobó
- `precio` — precio encontrado ese día
- `objetivo` — tu precio objetivo
- `url` — enlace directo al producto
