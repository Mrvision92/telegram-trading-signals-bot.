import os, json, asyncio
from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, HTTPException, Query
import httpx

# --- Env ---
BOT_TOKEN  = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID    = os.environ["TELEGRAM_CHAT_ID"]
SECRET     = os.environ.get("SECRET_TOKEN", "abc123")  # même valeur que dans l’URL TradingView

BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

app = FastAPI(title="TV → Telegram bridge")

# --------- Utils ----------
def base_symbol(tv_symbol: str) -> str:
    """
    Convertit un symbole TradingView en base symbol pour les news (BTCUSD -> BTC).
    """
    s = tv_symbol.upper()
    for suffix in ("USD", "USDT", "EUR", "PERP", ".P", ".D"):
        if s.endswith(suffix):
            return s.replace(suffix, "")
    # Ex: XAUUSD -> XAU (3 premières lettres)
    if len(s) >= 3:
        return s[:3]
    return s

def num(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None

def fmt_price(x: Any) -> str:
    try:
        return f"{float(x):,.2f}".replace(",", " ").replace(".00", "")
    except Exception:
        return str(x)

async def send_telegram(text: str) -> None:
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(BOT_API, json=payload)
        r.raise_for_status()

def build_human_message(msg: Dict[str, Any]) -> str:
    """
    Construit un message Telegram propre à partir du message JSON reçu de Pine.
    Le message Pine attendu ressemble à :
    {
      "symbol":"BTCUSD","timeframe":"4H","side":"BUY",
      "entry": "59250", "sl":"58500","tp1":"60200","tp2":"61800",
      "confidence": "82","ctx":"breakout+ema+vol"
    }
    """
    symbol     = str(msg.get("symbol", ""))
    tf         = str(msg.get("timeframe", ""))
    side       = str(msg.get("side", "")).upper()
    entry      = fmt_price(msg.get("entry"))
    sl         = fmt_price(msg.get("sl"))
    tp1        = fmt_price(msg.get("tp1"))
    tp2        = fmt_price(msg.get("tp2"))
    conf       = num(msg.get("confidence"))
    conf_str   = f"{int(conf)}%" if conf is not None else "—"
    ctx        = str(msg.get("ctx", ""))

    # Emoji direction
    arrow = "🟢 BUY" if side == "BUY" else "🔴 SELL" if side == "SELL" else "⚪"

    text = (
        f"*{arrow} — {symbol} ({tf})*\n"
        f"• *Entrée* : `{entry}`\n"
        f"• *SL*     : `{sl}`\n"
        f"• *TP1*    : `{tp1}`\n"
        f"• *TP2*    : `{tp2}`\n"
        f"• *Confiance* : *{conf_str}*\n"
        f"• *Contexte* : `{ctx}`"
    )
    return text

def extract_signal(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    TradingView envoie un JSON avec un champ 'message' (string).
    Ce 'message' contient notre JSON formaté par Pine.
    """
    if "message" in payload and isinstance(payload["message"], str):
        try:
            return json.loads(payload["message"])
        except Exception:
            # si ce n’est pas un JSON : on tente de parser clé=val ; sinon raw
            return {"raw_message": payload["message"]}
    return payload

# --------- Routes ----------
@app.get("/healthz")
async def healthz():
    return {"ok": True}

@app.get("/manual-signal")
async def manual_signal(text: str = "Hello depuis Render"):
    await send_telegram(text)
    return {"ok": True, "sent": text}

@app.post("/webhook")
async def webhook(request: Request, secret: str = Query(None)):
    if secret != SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    data = await request.json()
    signal = extract_signal(data)
    # si on n’a pas du JSON structuré, on envoie brut pour debug
    if "symbol" not in signal:
        await send_telegram(f"⚠️ Payload non structuré :\n\n`{json.dumps(signal, ensure_ascii=False)}`")
        return {"ok": True, "note": "unstructured"}

    text = build_human_message(signal)

    # (Optionnel) ici on pourrait enrichir avec des news si tu ajoutes un service
    # ex : news = await fetch_news(base_symbol(signal["symbol"]))
    # puis text += "\n\n📰 " + news[0]["title"]

    await send_telegram(text)
    return {"ok": True}
