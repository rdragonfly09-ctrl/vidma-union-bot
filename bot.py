# -*- coding: utf-8 -*-
import os
import logging
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import Executor

# ---- Конфіг через змінні середовища ----
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or 0)
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "wh_secret_777")
BASE_URL = os.getenv("BASE_URL", "").rstrip("/")  # https://your-service.onrender.com

if not BOT_TOKEN or not BASE_URL:
    raise RuntimeError("BOT_TOKEN і BASE_URL повинні бути задані у змінних середовища.")

WEBHOOK_PATH = f"/webhook/{WEBHOOK_SECRET}"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"

# ---- Логи ----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# ---- Aiogram 2.x ----
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

# ---- FastAPI ----
app = FastAPI()

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@dp.message_handler(commands=["start"])
async def cmd_start(msg: types.Message):
    await msg.answer("Вітаю! Бот працює ✅")

# ---- Підключення вебхука під час запуску ----
async def on_startup(dp: Dispatcher):
    # скинути старий вебхук і поставити новий
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    if ADMIN_ID:
        try:
            await bot.send_message(ADMIN_ID, "Бот запущений на Render ✅")
        except Exception:
            pass
    logger.info(f"Webhook set to: {WEBHOOK_URL}")

async def on_shutdown(dp: Dispatcher):
    await bot.delete_webhook()

# ---- Отримання апдейтів від Telegram (вебхук) ----
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = types.Update.to_object(data)
    Dispatcher.set_current(dp)
    Bot.set_current(bot)
    await dp.process_update(update)
    return {"ok": True}

# ---- Інтегруємо aiogram executor з FastAPI ----
executor = Executor(dp)
executor.on_startup(on_startup)
executor.on_shutdown(on_shutdown)

# uvicorn шукатиме змінну 'app'
# Старт відбувається командою в Render: uvicorn bot:app --host 0.0.0.0 --port $PORT
