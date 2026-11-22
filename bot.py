import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiohttp import web
from google import genai

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
ai_client = genai.Client(api_key=GEMINI_API_KEY)


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Привет! Напиши мне сообщение, и я отвечу.")


def generate_reply(prompt: str) -> str:
    try:
        response = ai_client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
        )
    except Exception as e:
        if "503" in str(e):
            response = ai_client.models.generate_content(
                model="gemini-3.8-flash-lite",
                contents=prompt,
            )
        else:
            raise
    return response.text or "Не удалось сформировать ответ."


@dp.message()
async def handle_message(message: types.Message):
    if not message.text:
        await message.answer("Пока понимаю только текстовые сообщения.")
        return

    try:
        reply_text = await asyncio.to_thread(generate_reply, message.text)
    except Exception as e:
        if "503" in str(e):
            await message.answer("Серверы Gemini сейчас перегружены, попробуйте ещё раз через пару секунд.")
            return
        await message.answer("Произошла ошибка при обращении к Gemini. Попробуйте чуть позже.")
        raise

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


async def main():
    await start_web_server()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
