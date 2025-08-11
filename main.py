import os
from fastapi import FastAPI, Request, HTTPException
import httpx
import uvicorn

# ========= Config =========
TELEGRAM_BOT_TOKEN = "7717198300:AAFw4OzeOAjC6dp9-2sD4VB8oy0f3R9_31E"
TELEGRAM_CHAT_ID   = "1382648204"
WEBHOOK_SECRET     = "abc123"  # change-le si tu veux

BOT_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

app = FastAPI()

async def send_telegram(message: str):
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(BOT_API_URL, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})
        r.raise_for_status()

@app.get("/")
@app.get("/health")
async def health():
    return {"ok": True}

def extract_message_from_request_body(raw: bytes) -> str | None:
    """
    Essaie d'extraire un message depuis le corps de la requête.
    - JSON TradingView typique: {"message":"..."} ou {"text":"..."}
    - Texte brut: b"..."
    - Vide: None
    """
    if not raw:
        return None
    try:
        import json
        data = json.loads(raw.decode("utf-8", errors="ignore"))
        # TradingView peut utiliser "message" ou "text"
        msg = data.get("message") or data.get("text")
        if isinstance(msg, str) and msg.strip():
            return msg.strip()
    except Exception:
        # pas du JSON: traiter comme texte brut
        txt = raw.decode("utf-8", errors="ignore").strip()
        if txt:
            return txt
    return None

# Accepte GET et POST pour éviter le "Method Not Allowed"
@app.get("/webhook")
@app.post("/webhook")
async def webhook(request: Request, secret: str | None = None, text: str | None = None):
    # 1) Vérif du secret (dans l'URL)
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    # 2) Récup du message
    raw = await request.body()
    body_msg = extract_message_from_request_body(raw)
    query_msg = (text or "").strip() if text else None

    message = body_msg or query_msg or "🚀 Nouveau signal détecté (aucun texte fourni)."

    # 3) Log utile pour debug
    try:
        print("WEBHOOK",
              {"method": request.method,
               "content_type": request.headers.get("content-type"),
               "len": len(raw) if raw else 0,
               "sample": (raw[:120] if raw else b"").decode("utf-8", errors="ignore")})
    except Exception:
        pass

    # 4) Envoi Telegram
    try:
        await send_telegram(message)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Telegram send failed: {e}") from e

    return {"status": "sent", "message": message}

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))  # Render injecte PORT
    uvicorn.run(app, host="0.0.0.0", port=port)
