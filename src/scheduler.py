import asyncio
from datetime import datetime, time
from aiogram import Bot
from subscription_checker import check_and_remove_expired_subscriptions


async def schedule_daily_check(bot: Bot, channel_id: str, check_time: time = time(12, 0)):
    print(f"Планировщик запущен. Ежедневная проверка в {check_time.strftime('%H:%M')}")
    
    while True:
        now = datetime.now()
        current_time = now.time()
        
        if current_time < check_time:
            next_check = datetime.combine(now.date(), check_time)
        else:
            from datetime import timedelta
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