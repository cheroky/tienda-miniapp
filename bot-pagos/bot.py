#!/usr/bin/env python3
"""
Bot de pagos con tarjeta para la tienda (Telegram Payments).

USA UN BOT NUEVO, SOLO PARA LA TIENDA. No uses @Pichinguin_ayudante_bot:
ese bot está conectado a GroupHelp por webhook y este programa usa getUpdates,
que no funciona mientras haya un webhook (y borrarlo rompería GroupHelp).

Qué hace:
  1. POST /factura  <- la mini app manda el pedido + initData de Telegram.
     Verifica la firma de initData, calcula el total con products.json (no se
     confía en precios del navegador) y crea la factura con createInvoiceLink.
  2. Escucha getUpdates: aprueba pre_checkout_query y, cuando llega
     successful_payment, le avisa al vendedor (SELLER_CHAT_ID) con el pedido.

Variables de entorno:
  TELEGRAM_BOT_TOKEN                token del bot NUEVO de la tienda (BotFather)
  TELEGRAM_PAYMENT_PROVIDER_TOKEN   BotFather > tu bot > Payments > Stripe
  SELLER_CHAT_ID                    5495133882 (Piero)
  PRODUCTS_URL                      https://cheroky.github.io/tienda-miniapp/products.json
  PORT                              8080 (por defecto)
Solo librería estándar de Python 3.9+.
"""
import hashlib, hmac, json, os, threading, time, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
PROVIDER = os.environ.get("TELEGRAM_PAYMENT_PROVIDER_TOKEN", "")
SELLER = int(os.environ.get("SELLER_CHAT_ID", "5495133882"))
PRODUCTS_URL = os.environ.get("PRODUCTS_URL", "https://cheroky.github.io/tienda-miniapp/products.json")
PORT = int(os.environ.get("PORT", "8080"))
API = f"https://api.telegram.org/bot{TOKEN}/"
PEDIDOS = {}  # payload -> datos del pedido (en memoria; suficiente para empezar)


def tg(method, **params):
    data = json.dumps(params).encode()
    req = urllib.request.Request(API + method, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=70) as r:
        j = json.load(r)
    if not j.get("ok"):
        raise RuntimeError(j)
    return j["result"]


def verificar_init_data(init_data, max_edad=86400):
    """Devuelve el usuario si la firma de Telegram es válida; si no, None."""
    campos = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    firma = campos.pop("hash", None)
    if not firma:
        return None
    check = "\n".join(f"{k}={v}" for k, v in sorted(campos.items()))
    secreto = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(hmac.new(secreto, check.encode(), hashlib.sha256).hexdigest(), firma):
        return None
    if time.time() - int(campos.get("auth_date", 0)) > max_edad:
        return None
    return json.loads(campos.get("user", "{}"))


def productos():
    with urllib.request.urlopen(PRODUCTS_URL + "?v=" + str(int(time.time())), timeout=15) as r:
        return {p["id"]: p for p in json.load(r)}


def crear_factura(body):
    if not PROVIDER:
        return {"error": "Falta TELEGRAM_PAYMENT_PROVIDER_TOKEN"}
    user = verificar_init_data(body.get("initData", ""))
    if not user:
        return {"error": "initData inválido"}
    catalogo = productos()
    precios, lineas = [], []
    for it in body.get("items", []):
        p, n = catalogo.get(it.get("id")), int(it.get("n", 0))
        if not p or n <= 0 or n > int(p.get("disponibles", 1)):
            return {"error": f"Artículo no disponible: {it.get('id')}"}
        centavos = int(round(float(p["precio"]) * 100)) * n
        precios.append({"label": f"{n} × {p['nombre']} (talla {p['talla']})"[:64], "amount": centavos})
        lineas.append(f"• {n} × {p['nombre']} — talla {p['talla']} — ${centavos / 100:.2f}")
    if not precios:
        return {"error": "Carrito vacío"}
    pedido = str(body.get("pedido", ""))[:16] or "P" + str(int(time.time()))
    payload = f"{pedido}:{user['id']}"
    total = sum(x["amount"] for x in precios) / 100
    PEDIDOS[payload] = {"user": user, "lineas": lineas, "total": total,
                        "telefono": str(body.get("telefono", ""))[:40], "nota": str(body.get("nota", ""))[:500]}
    link = tg("createInvoiceLink", title=f"Pedido {pedido}", description="Artículos de segunda mano",
              payload=payload, provider_token=PROVIDER, currency="USD", prices=precios,
              need_name=True, need_phone_number=True, need_shipping_address=True)
    return {"link": link}


def avisar_pago(msg):
    sp = msg["successful_payment"]
    d = PEDIDOS.pop(sp["invoice_payload"], {})
    u = msg.get("from", {})
    info = sp.get("order_info", {})
    dire = info.get("shipping_address", {})
    texto = "\n".join(filter(None, [
        f"💳 PAGADO con tarjeta — Pedido {sp['invoice_payload'].split(':')[0]}",
        *d.get("lineas", []),
        f"Total cobrado: ${sp['total_amount'] / 100:.2f} {sp['currency']}",
        f"Cliente: {u.get('first_name', '')} {u.get('last_name', '')}".strip() + (f" (@{u['username']})" if u.get("username") else "") + f" · id {u.get('id')}",
        f"Nombre: {info.get('name')}" if info.get("name") else "",
        f"Teléfono: {info.get('phone_number') or d.get('telefono')}" if (info.get("phone_number") or d.get("telefono")) else "",
        "Dirección: " + ", ".join(filter(None, [dire.get("street_line1"), dire.get("street_line2"), dire.get("city"), dire.get("state"), dire.get("post_code")])) if dire else "",
        f"Nota: {d['nota']}" if d.get("nota") else "",
        f"Stripe: {sp.get('provider_payment_charge_id')}",
    ]))
    tg("sendMessage", chat_id=SELLER, text=texto)
    tg("sendMessage", chat_id=msg["chat"]["id"], text="¡Gracias! Tu pago se recibió y el vendedor ya tiene tu pedido.")


def escuchar():
    offset = 0
    while True:
        try:
            for up in tg("getUpdates", offset=offset, timeout=50, allowed_updates=["message", "pre_checkout_query"]):
                offset = up["update_id"] + 1
                if "pre_checkout_query" in up:
                    tg("answerPreCheckoutQuery", pre_checkout_query_id=up["pre_checkout_query"]["id"], ok=True)
                elif up.get("message", {}).get("successful_payment"):
                    avisar_pago(up["message"])
        except Exception as e:
            print("getUpdates:", e)
            time.sleep(5)


class Manejador(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "https://cheroky.github.io")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()

    def do_POST(self):
        if self.path.rstrip("/") != "/factura":
            self.send_response(404); self.end_headers(); return
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
            res = crear_factura(body)
        except Exception as e:
            res = {"error": str(e)}
        out = json.dumps(res).encode()
        self.send_response(200); self._cors()
        self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(out)


if __name__ == "__main__":
    threading.Thread(target=escuchar, daemon=True).start()
    print(f"Bot de pagos escuchando en el puerto {PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Manejador).serve_forever()
