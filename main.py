import os
from fastapi import FastAPI, Request, HTTPException
import httpx
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # BotFather token
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")      # ex: -1001234567890
SECRET_TOKEN = os.getenv("SECRET_TOKEN")              # ton secret

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Missing TELEGRAM_BOT_TOKEN in environment")
if not TELEGRAM_CHAT_ID:
    raise RuntimeError("Missing TELEGRAM_CHAT_ID in environment")
if not SECRET_TOKEN:
    raise RuntimeError("Missing SECRET_TOKEN in environment")

BOT_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

app = FastAPI()

def format_signal_message(payload: dict) -> str:
    symbol = payload.get("symbol", "UNKNOWN")
    side = payload.get("side", "N/A")
    entry = payload.get("entry", "N/A")
    sl = payload.get("sl", "N/A")
    tp1 = payload.get("tp1", "N/A")
    tp2 = payload.get("tp2", "N/A")
    timeframe = payload.get("timeframe", "H1")
    confidence = payload.get("confidence", "—")
    reason = payload.get("reason", "")
    risk = payload.get("risk", None)  # % du capital

    lines = [
        f"📣 *Signal {side.upper()}* – *{symbol}* ({timeframe})",
        f"• Entrée : *{entry}*",
        f"• SL : *{sl}*",
        f"• TP1 : *{tp1}*",
        f"• TP2 : *{tp2}*",
        f"• Confiance : *{confidence}*",
    ]
    if risk is not None:
        lines.append(f"• Risque : *{risk}%* du capital")
    if reason:
        lines.append(f"🧠 Raison : {reason}")
    lines.append("—\nℹ️ Bot de signaux. Ajustez niveaux selon votre plan.")
    return "\n".join(lines)

async def send_telegram(text: str, chat_id: str = None):
    if chat_id is None:
        chat_id = TELEGRAM_CHAT_ID
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(BOT_API_URL, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        })
        resp.raise_for_status()
        return resp.json()

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/tv")
async def tradingview_webhook(request: Request, secret: str = ""):
    if secret != SECRET_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid secret")
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    text = format_signal_message(payload)
    await send_telegram(text)
    return {"status": "sent"}

@app.post("/manual-signal")
async def manual_signal(body: dict):
    if body.get("secret") != SECRET_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid secret")
    text = format_signal_message(body)
    await send_telegram(text)
    return {"status": "sent"}
# Route de test pour vérifier que l'app est en ligne
@app.get("/health")
def health_check():
    return {"ok": True}

# Route pour recevoir les signaux
@app.post("/webhook")
async def webhook(request: Request):
    # Vérification du token secret dans l'en-tête Authorization
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = auth_header.split(" ")[1]
    if token != SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid secret token")

    # Récupération des données envoyées
    payload = await request.json()

    # Envoi du message formaté au canal Telegram
    message = format_signal_message(payload)
    async with httpx.AsyncClient() as client:
        await client.post(
            BOT_API_URL,
            data={"chat_id": TELEGRAM_CHAT_ID, "text": message}
        )

    return {"status": "Signal sent to Telegram"}