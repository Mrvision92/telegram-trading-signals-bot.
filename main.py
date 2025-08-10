import os
from fastapi import FastAPI, Request, HTTPException
import httpx
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")   # ex: -1002781479267
SECRET_TOKEN = os.getenv("SECRET_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Missing TELEGRAM_BOT_TOKEN in environment")
if not TELEGRAM_CHAT_ID:
    raise RuntimeError("Missing TELEGRAM_CHAT_ID in environment")
if not SECRET_TOKEN:
    raise RuntimeError("Missing SECRET_TOKEN in environment")

BOT_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

app = FastAPI()


def format_signal_message(payload: dict) -> str:
    # Autorise à poster soit un 'text' brut, soit un bloc 'signal' détaillé
    if "text" in payload:
        return str(payload["text"])

    symbol = payload.get("symbol", "UNKNOWN")
    side = payload.get("side", "N/A").upper()
    entry = payload.get("entry", "N/A")
    sl = payload.get("sl", "N/A")
    tp1 = payload.get("tp1", "N/A")
    tp2 = payload.get("tp2", "N/A")
    timeframe = payload.get("timeframe", "H1")
    confidence = payload.get("confidence", "-")
    reason = payload.get("reason", "")
    risk = payload.get("risk", None)

    lines = [
        f"📈 {symbol} — {timeframe}",
        f"➡️ {side}",
        f"🎯 Entrée : {entry}",
        f"🛑 SL : {sl}",
        f"🎯 TP1 : {tp1} | TP2 : {tp2}",
        f"🔎 Confiance : {confidence}",
    ]
    if reason:
        lines.append(f"📝 Raison : {reason}")
    if risk is not None:
        lines.append(f"⚠️ Risque : {risk}% du capital")
    return "\n".join(lines)


async def send_telegram(text: str):
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(BOT_API_URL, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        })
        resp.raise_for_status()


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/manual-signal")
async def manual_signal(body: dict):
    # secret attendu DANS le body JSON
    if body.get("secret") != SECRET_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid secret")
    text = format_signal_message(body)
    await send_telegram(text)
    return {"status": "sent"}


@app.post("/webhook")
async def webhook(request: Request):
    # secret attendu en Bearer token (onglet Auth -> Bearer Token)
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = auth.split(" ", 1)[1]
    if token != SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid secret token")

    payload = await request.json()
    text = format_signal_message(payload)
    await send_telegram(text)
    return {"status": "sent"}
