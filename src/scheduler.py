import asyncio
from datetime import datetime, time, timedelta
from aiogram import Bot
from subscription_checker import check_and_remove_expired_subscriptions
from db import process_donations


async def schedule_hourly_donations_sync(access_token: str):
    print(f"Планировщик синхронизации донатов запущен. Проверка каждый час")
    while True:
        try:
            now = datetime.now()
            print(f"\n[{now}] Начало синхронизации донатов...")

            end_date = now
            start_date = now - timedelta(hours=1)

            stats = process_donations(start_date, end_date, access_token)

            if stats:
                print(f"✓ Синхронизация завершена:")
                print(f"  - Всего обработано: {stats['total']}")
                print(f"  - Добавлено новых: {stats['inserted']}")
                print(f"  - Обновлено: {stats['updated']}")
                print(f"  - Ошибок: {stats['failed']}")
            else:
                print("✓ Новых донатов не найдено")

        except Exception as e:
            print(f"✗ Ошибка при синхронизации донатов: {e}")
        
        print(f"Следующая синхронизация через 1 час...")
        await asyncio.sleep(3600)

async def schedule_daily_check(bot: Bot, channel_id: str, check_time: time = time(12, 0)):
    print(f"Планировщик запущен. Ежедневная проверка в {check_time.strftime('%H:%M')}")
    
    while True:
        now = datetime.now()
        current_time = now.time()
        
        if current_time < check_time:
            next_check = datetime.combine(now.date(), check_time)
        else:
            next_check = datetime.combine(now.date() + timedelta(days=1), check_time)
        
        wait_seconds = (next_check - now).total_seconds()
        
        print(f"Следующая проверка: {next_check.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Ожидание: {wait_seconds / 3600:.2f} часов")
        
        await asyncio.sleep(wait_seconds)
        
        try:
            await check_and_remove_expired_subscriptions(bot, channel_id)
        except Exception as e:
            print(f"Ошибка при выполнении проверки: {e}")
        
        await asyncio.sleep(60)


async def run_immediate_check(bot: Bot, channel_id: str):
    print("Запуск немедленной проверки...")
    await check_and_remove_expired_subscriptions(bot, channel_id)

async def run_immediate_sync(access_token: str):
    print("Запуск немедленной синхронизации донатов...")
    now = datetime.now()
    end_date = now
    start_date = now - timedelta(hours=1)

    try:
        stats = process_donations(start_date, end_date, access_token)
        if stats:
            print(f"✓ Синхронизация завершена:")
            print(f"  - Всего обработано: {stats['total']}")
            print(f"  - Добавлено новых: {stats['inserted']}")
            print(f"  - Обновлено: {stats['updated']}")
            print(f"  - Ошибок: {stats['failed']}")
        return stats
    except Exception as e:
        print(f"✗ Ошибка при синхронизации: {e}")
        return None