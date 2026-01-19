import asyncio
import sys
from os import environ

from decouple import config
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from filters.chat_type import IsPrivateChat  
from handlers.user.message import router as user_router

async def main():
    environ['TZ'] = 'Europe/Moscow'

    bot = Bot(
        token=config("BOT_TOKEN"),
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )

    bot_info = await bot.get_me()

    dp = Dispatcher(bot=bot)
    dp.include_router(user_router)

    dp.message.filter(IsPrivateChat())

    print(f'Bot {bot_info.full_name} started (@{bot_info.username}. ID: {bot_info.id})')

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped!")
