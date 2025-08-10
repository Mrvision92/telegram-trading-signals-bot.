import os
from fastapi import FastAPI, Request, HTTPException
import httpx
from dotenv import load_dotenv

# Charge .env si présent (utile en local)
load_dotenv()

# ── Variables d'environnement ────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")      # token BotFather
TELEGRAM_CHAT_ID  = os.getenv("TELEGRAM_CHAT_ID")         # ex: -1002781479267
SECRET_TOKEN      = os.getenv("SECRET_TOKEN")             # ex: Emilio2117

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Missing TELEGRAM_BOT_TOKEN in environment")
if not TELEGRAM_CHAT_ID:
    raise RuntimeError("Missing TELEGRAM_CHAT_ID in environment")
if not SECRET_TOKEN:
    raise RuntimeError("Missing SECRET_TOKEN in environment")

BOT_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# ── App FastAPI ──────────────────────────────────────────────────────────────
app = FastAPI()

# Accueil & health pour Render
@app.get("/")
async def root():
    return {"ok": True}

@app.get("/health")
async def health():
    return {"ok": True}

# ── Helpers ─────────────────────────────────────────────────────────────────
def format_signal_message(payload: dict) -> str:
    """
    Si 'text' est fourni -> envoie tel quel.
    Sinon, formate un message de signal à partir des champs.
    """
    if "text" in payload:
        return str(payload["text"])

    symbol     = payload.get("symbol", "UNKNOWN")
    side       = payload.get("side", "N/A").upper()
    entry      = payload.get("entry", "N/A")
    sl         = payload.get("sl", "N/A")
    tp1        = payload.get("tp1", "N/A")
    tp2        = payload.get("tp2", "N/A")
    timeframe  = payload.get("timeframe", "H1")
    confidence = payload.get("confidence", "-")
    reason     = payload.get("reason", "")
    risk       = payload.get("risk", None)

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

async def send_to_telegram(text: str):
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(
            BOT_API_URL,
            data={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
        )
        r.raise_for_status()

# ── Routes d’envoi ──────────────────────────────────────────────────────────
# A) Test simple depuis le navigateur: GET /manual-signal?text=Hello
@app.get("/manual-signal")
async def manual_signal(text: str):
    await send_to_telegram(text)
    return {"status": "sent", "message": text}

# B) POST sans Auth (le secret est DANS le body) – pratique pour ReqBin/Postman
@app.post("/manual-signal")
async def manual_signal_post(body: dict):
    if body.get("secret") != SECRET_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid secret")
    text = format_signal_message(body)
    await send_to_telegram(text)
    return {"status": "sent"}

# C) POST avec Auth Bearer (le secret est dans l'en-tête Authorization)
@app.post("/webhook")
async def webhook(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = auth.split(" ", 1)[1]
    if token != SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid secret token")

    payload = await request.json()
    text = format_signal_message(payload)
    await send_to_telegram(text)
    return {"status": "sent"}
