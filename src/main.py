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
from logger_config import setup_logger

logger = setup_logger(__name__)

async def main():
    environ['TZ'] = 'Europe/Moscow'

    BOT_TOKEN = config("BOT_TOKEN")
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )

    bot_info = await bot.get_me()
    logger.info(f"Бот запущен: {bot_info.full_name} (@{bot_info.username}, ID: {bot_info.id})")

    dp = Dispatcher(bot=bot)

    dp.include_router(user_router)
    dp.include_router(admin_router)

    dp.message.filter(IsPrivateChat())

    CHANNEL_ID = config("CHANNEL_ID")
    ACCESS_TOKEN = config("ACCESS_TOKEN")

    CHECK_HOUR = int(config("CHECK_HOUR", default="12"))
    CHECK_MINUTE = int(config("CHECK_MINUTE", default="0"))
    check_time = time(CHECK_HOUR, CHECK_MINUTE)

    logger.info(f"Настройки: CHANNEL_ID={CHANNEL_ID}, CHECK_TIME={check_time}")

    asyncio.create_task(schedule_daily_check(bot, CHANNEL_ID, check_time))
    asyncio.create_task(schedule_hourly_donations_sync(ACCESS_TOKEN))

    logger.info("Фоновые задачи запущены, начало polling...")

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Критическая ошибка при работе бота: {e}", exc_info=True)
        raise
    finally:
        await bot.session.close()
        logger.info("Бот остановлен, сессия закрыта")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем (KeyboardInterrupt/SystemExit)")
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске бота: {e}", exc_info=True)
        sys.exit(1)
