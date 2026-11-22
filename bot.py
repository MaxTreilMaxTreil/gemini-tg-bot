import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
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
      model="gemini-2.5-flash",
      contents=message.text,
  )
  await message.answer(
      response.text or "Не удалось сформировать ответ."
  )


async def main():
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
