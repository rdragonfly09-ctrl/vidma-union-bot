import os
import hmac
import hashlib
import json
import typing as t

import requests
from fastapi import FastAPI, Request, HTTPException, Header

BOT_TOKEN = os.environ["BOT_TOKEN"]
BASE_URL = os.environ["BASE_URL"].rstrip("/")          # наприклад: https://vidma-union-bot.onrender.com
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")       # необов'язково
ADMIN_ID = os.getenv("ADMIN_ID")                       # необов'язково

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = FastAPI(title="Telegram Bot (FastAPI+requests)")

def tg_send_chat_action(chat_id: int, action: str = "typing") -> None:
    try:
        requests.post(f"{TELEGRAM_API}/sendChatAction", json={"chat_id": chat_id, "action": action}, timeout=10)
    except Exception:
        pass

def tg_send_message(chat_id: int, text: str, disable_web_page_preview: bool = True) -> None:
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": disable_web_page_preview,
        "parse_mode": "HTML",
    }
    requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=15)

def set_webhook(url: str) -> bool:
    payload = {"url": url}
    if WEBHOOK_SECRET:
        payload["secret_token"] = WEBHOOK_SECRET
    r = requests.post(f"{TELEGRAM_API}/setWebhook", json=payload, timeout=15)
    try:
        data = r.json()
    except Exception:
        return False
    return bool(data.get("ok"))

@app.on_event("startup")
def on_startup():
    # реєструємо вебхук
    wh_url = f"{BASE_URL}/webhook/{BOT_TOKEN}"
    ok = set_webhook(wh_url)
    if not ok:
        print("Failed to set webhook. Check BASE_URL and token.")
    else:
        print(f"Webhook set to {wh_url}")

def verify_secret(header_token: t.Optional[str]) -> None:
    if not WEBHOOK_SECRET:
        return
    if not header_token or header_token != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid secret token")

@app.post("/webhook/{token}")
async def telegram_webhook(token: str, request: Request, x_telegram_bot_api_secret_token: t.Optional[str] = Header(None)):
    # 1) токен у шляху має збігатися (проста перевірка адреси вебхука)
    if token != BOT_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid path token")

    # 2) (опційно) перевіряємо секретний заголовок від Telegram
    verify_secret(x_telegram_bot_api_secret_token)

    update = await request.json()

    # Підтримка повідомлень
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "") or ""

        tg_send_chat_action(chat_id)

        if text.startswith("/start"):
            tg_send_message(chat_id,
                "Вітаю! Я асистент. Надішли мені будь-який текст — я відповім.\n"
                "Щоб змінити текст — просто напиши нове повідомлення."
            )
        else:
            reply = f"Ти написала: <b>{text}</b>\nЯ працюю на Render без aiohttp 😉"
            tg_send_message(chat_id, reply)

    # Можна додати інші типи оновлень (callback_query, my_chat_member тощо)

    return {"ok": True}

@app.get("/")
def root():
    return {"status": "ok", "webhook": f"{BASE_URL}/webhook/{BOT_TOKEN}"}
