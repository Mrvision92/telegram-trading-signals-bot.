import os
from fastapi import FastAPI, Request, HTTPException
import httpx
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # ex: -1002781479267
SECRET_TOKEN = os.getenv("SECRET_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError('Missing TELEGRAM_BOT_TOKEN in environment')
if not TELEGRAM_CHAT_ID:
    raise RuntimeError('Missing TELEGRAM_CHAT_ID in environment')
if not SECRET_TOKEN:
    raise RuntimeError('Missing SECRET_TOKEN in environment')

BOT_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

app = FastAPI()

# ✅ Route racine pour test Render
@app.get("/")
async def root():
    return {"ok": True}

def format_signal_message(payload: dict) -> str:
    # Autorise à poster soit un 'text' brut, soit un bloc 'signal' détaillé
    if "text" in payload:
        return str(payload["text"])

    symbol = payload.get("symbol", "UNKNOWN")
    side = payload.get("side", "N/A").upper()
    price = payload.get("price", "N/A")
    return f"Signal: {symbol} - {side} à {price}"

@app.post("/webhook")
async def webhook(request: Request):
    token = request.headers.get("X-SECRET-TOKEN")
    if token != SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid secret token")

    payload = await request.json()
    message = format_signal_message(payload)

    async with httpx.AsyncClient() as client:
        r = await client.post(BOT_API_URL, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        })
        if r.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to send message to Telegram")

    return {"ok": True}
    @app.get("/manual-signal")
async def manual_signal(text: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            BOT_API_URL,
            data={"chat_id": TELEGRAM_CHAT_ID, "text": text}
        )
    return {"status": "sent", "message": text}
