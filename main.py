import os
from fastapi import FastAPI, Request, HTTPException
import httpx
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")      # ex: 7717...:AA...
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")        # ex: 1382648204
SECRET_TOKEN       = os.getenv("SECRET_TOKEN", "abc123")  # doit matcher le ?secret=...

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in environment")

BOT_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

app = FastAPI()

# --- petite aide ---
@app.get("/")
async def root():
    return {"ok": True, "msg": "Service up"}

def _fmt_tv_message(payload: dict) -> str:
    s = payload.get
    parts = [
        f"Actif : {s('symbol', 'N/A')}",
        f"Type : {s('side','N/A')}",
        f"Prix entrée : {s('entry','N/A')}",
        f"Stop Loss : {s('sl','N/A')}",
        f"TP1 : {s('tp1','N/A')}",
        f"TP2 : {s('tp2','N/A')}",
    ]
    if "confidence" in payload:
        parts.append(f"Confiance : {s('confidence')}%")
    if "reason" in payload and s('reason'):
        parts.append(f"Contexte : {s('reason')}")
    return "\n".join(parts)

# --- endpoint pour TradingView (POST JSON) ---
@app.post("/webhook")
async def webhook(request: Request, secret: str = ""):
    if secret != SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid secret token")
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    text = _fmt_tv_message(payload) if payload else "Signal reçu."
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(BOT_API_URL, data={"chat_id": TELEGRAM_CHAT_ID, "text": text})
        if r.status_code != 200:
            raise HTTPException(status_code=500, detail="Fail to send to Telegram")
    return {"ok": True}

# --- endpoints de test ---
@app.get("/health")
def health():
    return {"ok": True}

@app.get("/manual-signal")
async def manual(text: str = "Hello depuis Render"):
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(BOT_API_URL, data={"chat_id": TELEGRAM_CHAT_ID, "text": text})
        r.raise_for_status()
    return {"status": "sent", "message": text}
