import asyncio
import logging
import os
import time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiohttp import web
from google import genai

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

if not TELEGRAM_TOKEN:
    raise RuntimeError("Не задана переменная окружения TELEGRAM_BOT_TOKEN.")
if not GEMINI_API_KEY:
    raise RuntimeError("Не задана переменная окружения GEMINI_API_KEY.")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
ai_client = genai.Client(api_key=GEMINI_API_KEY)


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    logger.info(
        "Получена команда /start от user_id=%s",
        message.from_user.id if message.from_user else "unknown",
    )
    await message.answer("Привет! Напиши мне сообщение, и я отвечу.")


def generate_reply_sync(prompt: str) -> str:
    delays = [1, 2]
    for attempt, delay in enumerate(delays):
        try:
            logger.info("Отправка запроса в Gemini (попытка %s)...", attempt + 1)
            response = ai_client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
            )
            text = getattr(response, "text", None)
            if text and text.strip():
                logger.info("Ответ от Gemini получен (длина %s символов)", len(text))
                return text.strip()
            return "Модель вернула пустой ответ. Попробуйте переформулировать запрос."
        except Exception as e:
            err_str = str(e)
            logger.warning("Ошибка на попытке %s: %s", attempt + 1, err_str)
            if "503" in err_str and attempt < len(delays) - 1:
                time.sleep(delay)
                continue
            raise


@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id if message.from_user else "unknown"
    if not message.text or not message.text.strip():
        await message.answer("Пока понимаю только текстовые сообщения.")
        return

    user_text = message.text.strip()
    logger.info("Получено сообщение от user_id=%s: %r", user_id, user_text[:100])

    try:
        reply_text = await asyncio.wait_for(
            asyncio.to_thread(generate_reply_sync, user_text),
            timeout=60.0,
        )
    except asyncio.TimeoutError:
        logger.error("Таймаут (60 сек) при ожидании ответа от Gemini для user_id=%s", user_id)
        await message.answer("Gemini отвечает слишком долго (таймаут). Попробуйте ещё раз.")
        return
    except Exception as e:
        err_str = str(e)
        logger.exception("Ошибка при обращении к Gemini для user_id=%s: %s", user_id, err_str)

        if "503" in err_str or "UNAVAILABLE" in err_str:
            await message.answer(
                "Серверы Gemini сейчас перегружены. Попробуйте отправить сообщение ещё раз через несколько секунд."
            )
            return
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
            await message.answer(
                "Превышен лимит запросов к Gemini API. Подождите немного и попробуйте снова."
            )
            return
        if "401" in err_str or "403" in err_str or "API_KEY" in err_str or "INVALID_ARGUMENT" in err_str:
            await message.answer(
                "Проблема с ключом GEMINI_API_KEY. Проверьте настройки ключа на хостинге."
            )
            return

        await message.answer("Произошла ошибка при обращении к Gemini. Попробуйте чуть позже.")
        return

    for i in range(0, len(reply_text), 4096):
        await message.answer(reply_text[i:i + 4096])


async def health_check(request):
    return web.Response(text="OK")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("HTTP health-check сервер запущен на порту %s", port)


async def main():
    await start_web_server()
    logger.info("Запуск polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
