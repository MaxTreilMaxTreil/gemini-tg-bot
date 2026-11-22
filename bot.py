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


@dp.message()
async def handle_message(message: types.Message):
  if not message.text:
    await message.answer("Пока понимаю только текстовые сообщения.")
    return

  response = ai_client.models.generate_content(
      model="gemini-3.8-flash",
      contents=message.text,
  )
  await message.answer(response.text or "Не удалось сформировать ответ.")


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
