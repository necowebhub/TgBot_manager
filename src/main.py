import asyncio
import sys
from os import environ
from datetime import time

from decouple import config
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from filters.chat_type import IsPrivateChat  
from handlers.user.message import router as user_router
from handlers.admin.commands import router as admin_router
from scheduler import schedule_daily_check, schedule_hourly_donations_sync

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
    dp.include_router(admin_router)

    dp.message.filter(IsPrivateChat())

    print(f'Bot {bot_info.full_name} started (@{bot_info.username}. ID: {bot_info.id})')

    CHANNEL_ID = config("CHANNEL_ID")

    ACCESS_TOKEN = config("ACCESS_TOKEN")

    CHECK_HOUR = int(config("CHECK_HOUR", default="12"))
    CHECK_MINUTE = int(config("CHECK_MINUTE", default="0"))
    check_time = time(CHECK_HOUR, CHECK_MINUTE)

    asyncio.create_task(schedule_daily_check(bot, CHANNEL_ID, check_time))

    asyncio.create_task(schedule_hourly_donations_sync(ACCESS_TOKEN))

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped!")
