import asyncio
from datetime import datetime, time, timedelta
from aiogram import Bot
from subscription_checker import check_and_remove_expired_subscriptions
from db import process_donations
from logger_config import setup_logger

logger = setup_logger(__name__)


async def schedule_hourly_donations_sync(access_token: str):
    logger.info("Планировщик синхронизации донатов запущен. Проверка каждый час")
    
    while True:
        try:
            now = datetime.now()
            logger.info(f"Начало синхронизации донатов...")

            end_date = now
            start_date = now - timedelta(hours=1)

            stats = process_donations(start_date, end_date, access_token)

            if stats:
                logger.info(
                    f"Синхронизация завершена - "
                    f"обработано: {stats['total']}, "
                    f"добавлено: {stats['inserted']}, "
                    f"обновлено: {stats['updated']}, "
                    f"ошибок: {stats['failed']}"
                )
            else:
                logger.info("Новых донатов не найдено")

        except Exception as e:
            logger.error(f"Ошибка при синхронизации донатов: {e}", exc_info=True)
        
        logger.debug("Следующая синхронизация через 1 час...")
        await asyncio.sleep(3600)

async def schedule_daily_check(bot: Bot, channel_id: str, check_time: time = time(12, 0)):
    logger.info(f"Планировщик проверки подписок запущен. Ежедневная проверка в {check_time.strftime('%H:%M')}")
    
    while True:
        now = datetime.now()
        current_time = now.time()
        
        if current_time < check_time:
            next_check = datetime.combine(now.date(), check_time)
        else:
            next_check = datetime.combine(now.date() + timedelta(days=1), check_time)
        
        wait_seconds = (next_check - now).total_seconds()
        
        logger.info(
            f"Следующая проверка: {next_check.strftime('%Y-%m-%d %H:%M:%S')} "
            f"(через {wait_seconds / 3600:.2f} часов)"
        )
        
        await asyncio.sleep(wait_seconds)
        
        try:
            await check_and_remove_expired_subscriptions(bot, channel_id)
        except Exception as e:
            logger.error(f"Ошибка при выполнении проверки подписок: {e}", exc_info=True)
        
        await asyncio.sleep(60)


async def run_immediate_check(bot: Bot, channel_id: str):
    logger.info("Запуск немедленной проверки подписок...")
    await check_and_remove_expired_subscriptions(bot, channel_id)

async def run_immediate_sync(access_token: str):
    logger.info("Запуск немедленной синхронизации донатов...")
    now = datetime.now()
    end_date = now
    start_date = now - timedelta(hours=1)

    try:
        stats = process_donations(start_date, end_date, access_token)
        if stats:
            logger.info(
                f"Синхронизация завершена - "
                f"обработано: {stats['total']}, "
                f"добавлено: {stats['inserted']}, "
                f"обновлено: {stats['updated']}, "
                f"ошибок: {stats['failed']}"
            )
        return stats
    except Exception as e:
        logger.error(f"Ошибка при синхронизации: {e}", exc_info=True)
        return None
