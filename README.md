# Tienda (mini app de Telegram)

Tienda sencilla para vender artículos de segunda mano (ropa, zapatos, carteras, fajas, chancletas) dentro de Telegram.

**Enlace:** https://cheroky.github.io/tienda-miniapp/

## Cómo funciona
1. El cliente abre la tienda, filtra por categoría y toca **Agregar**.
2. En el carrito ajusta cantidades y toca **Hacer pedido**.
3. Elige cómo pagar, pone su teléfono o una nota (opcional) y toca **Enviar pedido**.
4. Se abre el chat con **@ch3r0ky** con el pedido ya escrito (artículos, tallas, precios, total, forma de pago, nombre, teléfono y nota). El cliente solo toca **Enviar ➤**.
5. Tú le contestas y cobras por Zelle o en efectivo.

No necesita servidor ni bot: es una página fija en GitHub Pages.

## Formas de pago
| Opción | Estado | Qué falta |
|---|---|---|
| 💵 Pagar al recibir / Zelle | **Funciona ya** | Nada |
| 🇭🇳 Transferencia o Tigo Money (Honduras) | **Funciona ya** | Opcional: poner tus datos de cuenta y el cambio |
| 💳 Tarjeta (Telegram Payments + Stripe) | Sale como "Pronto" | Bot nuevo + Stripe + servidor (ver abajo) |
| 💎 Gram / TON | Sale como "Pronto" | Poner tu dirección de billetera en `config.json` |

**Estrellas de Telegram (⭐) no se usan:** las reglas de Telegram solo permiten Estrellas para cosas digitales. Para ropa y artículos físicos está prohibido, así que la tienda no las ofrece.

### Transferencia o Tigo Money (Honduras)
El cliente ve el total también en lempiras (aprox.) y te llega el pedido con la línea
`Pago: Transferencia / Tigo Money (Honduras) — total aprox. L …` y `Manda la foto del comprobante en este chat`.
Antes de entregar, revisa que te llegó el dinero.

Todo se cambia en `config.json`, dentro de `"transferencia_hn"` (en GitHub: toca el archivo › ✏️ › Commit changes):
- **Datos de tu cuenta:** cambia `"instrucciones"`. Por ahora dice `Te mando los datos de la cuenta por este chat`. Puedes poner tus datos reales, por ejemplo:
  `"instrucciones": "BAC Honduras, cuenta 123456789 a nombre de Piero Castro · Tigo Money 9999-9999"`
  (Lo que pongas ahí lo ve cualquiera que abra la tienda.)
- **Cambio del lempira:** cambia `"lempiras_por_usd": 26.0` por el cambio del día (por ejemplo `26.4`). Usa punto, no coma.
- **Quitarla:** pon `"activo": false`.

### Activar Gram / TON
1. Copia la dirección de tu billetera (Wallet de Telegram › TON › Recibir, o Tonkeeper).
2. En `config.json` cambia `"wallet": "GRAM_WALLET_ADDRESS"` por tu dirección y `"activo": false` por `"activo": true` (dentro de `"ton"`).
3. El precio en TON se calcula con el cambio del momento (tonapi.io). Si no se puede consultar, usa `usd_por_ton` de `config.json`.

El cliente abre su billetera con el monto y el comentario `Pedido PXXXXX` ya puestos, paga, y luego toca **Ya pagué · enviar pedido**. **Revisa en tu billetera que llegó el pago** antes de entregar: la página no lo puede comprobar.

### Activar Tarjeta (más adelante)
Necesita un programa corriendo todo el tiempo (`bot-pagos/bot.py`):
1. En **@BotFather** crea un **bot nuevo solo para la tienda** (`/newbot`). No uses @Pichinguin_ayudante_bot: está conectado a GroupHelp y ese enlace se rompería.
2. En BotFather › tu bot nuevo › **Payments** › **Stripe** (primero pruébalo con "Stripe TEST"). Te da el *provider token*.
3. Sube `bot-pagos/bot.py` a un servidor con HTTPS (Render, Railway, Fly.io…) con estas variables:
   - `TELEGRAM_BOT_TOKEN` = token del bot nuevo
   - `TELEGRAM_PAYMENT_PROVIDER_TOKEN` = token de Stripe de BotFather
   - `SELLER_CHAT_ID` = `5495133882`
4. En BotFather pon la tienda en el bot nuevo: Bot Settings › Menu Button › `https://cheroky.github.io/tienda-miniapp/`. (La tarjeta solo funciona si la tienda se abre desde **ese** bot, porque la firma de Telegram es de ese bot.)
5. En `config.json`, dentro de `"tarjeta"`, pon `"api_url": "https://tu-servidor..."` y `"activo": true`.

El bot verifica que el pedido viene de Telegram, calcula el total con `products.json` (nadie puede cambiar el precio), crea la factura y, cuando el cliente paga, te manda el pedido con nombre, teléfono y dirección.

## Agregar o cambiar artículos
1. Sube la foto a la carpeta `fotos/` (GitHub › fotos › Add file › Upload files). Mejor cuadrada, JPG, menos de 300 KB.
2. Edita `products.json` (toca el archivo › ✏️) y copia un bloque así:
```json
{"id": "p9", "nombre": "Vestido rojo", "categoria": "Ropa", "talla": "M", "precio": 14, "estado": "Segunda mano · buen estado", "foto": "fotos/vestido-rojo.jpg", "disponibles": 1}
```
   - `id`: distinto para cada artículo.
   - `categoria`: exactamente `Ropa`, `Zapatos`, `Carteras`, `Fajas` o `Chancletas`.
   - `precio`: en dólares, sin `$`.
   - `disponibles`: cuántos tienes. Pon `0` cuando se venda y sale "Agotado".
   - Separa cada bloque con coma, sin coma después del último.
3. Toca **Commit changes**. En uno o dos minutos ya sale en la tienda.

Borra los 8 artículos que dicen "(Ejemplo)" y sus fotos `fotos/ejemplo-*.svg` cuando pongas los tuyos.

**Siguiente paso posible:** un bot donde le mandas una foto con el precio y la talla, y él agrega el artículo solo, sin editar archivos.

## Archivos
- `index.html` — la tienda.
- `products.json` — los artículos.
- `config.json` — nombre de la tienda, tu usuario de Telegram y formas de pago.
- `fotos/` — fotos de los artículos.
- `bot-pagos/bot.py` — bot de pagos con tarjeta (opcional, para después).
