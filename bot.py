import os
import requests
from fastapi import FastAPI, Request, HTTPException, Header

BOT_TOKEN = os.environ["BOT_TOKEN"]
BASE_URL = os.environ["BASE_URL"].rstrip("/")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
ADMIN_ID = os.getenv("ADMIN_ID")  # наприклад 6958136111

API = f"https://api.telegram.org/bot{BOT_TOKEN}"
app = FastAPI(title="Vidma Assistant")

# ---------- helpers ----------
def send(method: str, payload: dict):
    requests.post(f"{API}/{method}", json=payload, timeout=15)

def chat_action(chat_id: int, action="typing"):
    send("sendChatAction", {"chat_id": chat_id, "action": action})

def kb_main():
    return {
        "keyboard": [
            [{"text": "📝 Подати заявку"}],
            [{"text": "🔮 Діагностика (опис)"}],
            [{"text": "🕯 Підтримка"}],
            [{"text": "⬅️ Меню"}],
        ],
        "resize_keyboard": True,
    }

def reply(chat_id: int, text: str):
    send("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": kb_main()
    })

def set_webhook(url: str):
    payload = {"url": url}
    if WEBHOOK_SECRET:
        payload["secret_token"] = WEBHOOK_SECRET
    r = requests.post(f"{API}/setWebhook", json=payload, timeout=15)
    try:
        return r.json().get("ok", False)
    except Exception:
        return False

@app.on_event("startup")
def on_startup():
    wh = f"{BASE_URL}/webhook/{BOT_TOKEN}"
    if set_webhook(wh):
        print("Webhook set:", wh)
    else:
        print("Failed to set webhook")

def verify_secret(header_token):
    if not WEBHOOK_SECRET:
        return
    if header_token != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid secret token")

# ---------- handlers ----------
@app.post("/webhook/{token}")
async def webhook(token: str, request: Request,
                  x_telegram_bot_api_secret_token: str | None = Header(None)):
    if token != BOT_TOKEN:
        raise HTTPException(status_code=403, detail="Bad token")
    verify_secret(x_telegram_bot_api_secret_token)

    upd = await request.json()
    if "message" in upd:
        msg = upd["message"]
        chat_id = msg["chat"]["id"]
        text = (msg.get("text") or "").strip()
        username = msg["from"].get("username", "")
        name = (msg["from"].get("first_name","") + " " + msg["from"].get("last_name","")).strip()

        chat_action(chat_id)

        low = text.lower()

        if text.startswith("/start") or low == "⬅️ меню":
            reply(chat_id,
                  "Вітаю! Я асистент.\n\n"
                  "Обери дію нижче або просто напиши повідомлення — я передам його майстру.")
            return {"ok": True}

        if "подати заявку" in low:
            reply(chat_id,
                  "📝 <b>Подати заявку</b>\n\n"
                  "Напиши одним повідомленням:\n"
                  "• Ім’я\n"
                  "• @нік або посилання на профіль/канал\n"
                  "• Що потрібно (діагностика/навчання/інше)\n"
                  "• Короткий опис запиту.\n\n"
                  "Після надсилання я передам заявку та повернуся з відповіддю.")
            return {"ok": True}

        if "діагностика (опис)" in low:
            reply(chat_id,
                  "🔮 <b>Діагностика — як це працює</b>\n\n"
                  "• Я збираю запит і передаю майстру.\n"
                  "• Після підтвердження — оплата і час виконання.\n"
                  "• Результат ви отримуєте у форматі голосового/тексту.\n\n"
                  "Хочеш оформити запит — натисни «📝 Подати заявку».")
            return {"ok": True}

        if "підтримка" in low:
            reply(chat_id,
                  "🕯 <b>Підтримка</b>\n\n"
                  "Питання щодо навчання, діагностики, оплати й термінів — пиши тут. "
                  "Я передам повідомлення та поверну відповідь якнайшвидше.")
            return {"ok": True}

        # УСЕ ІНШЕ — вважаємо зверненням/заявкою та пересилаємо адміну
        if ADMIN_ID:
            info = (
                "📩 <b>Нове звернення</b>\n"
                f"• user: @{username or '—'} ({name or '—'})\n"
                f"• chat_id: <code>{chat_id}</code>\n"
                f"• text:\n{text}"
            )
            send("sendMessage", {"chat_id": int(ADMIN_ID), "text": info, "parse_mode": "HTML"})

        reply(chat_id, "Дякую! Заявку/повідомлення надіслано. Очікуйте відповіді 🕯")
    return {"ok": True}

@app.get("/")
def root():
    return {"status": "ok"}
