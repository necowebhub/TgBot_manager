from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from decouple import config
from filters.chat_type import IsPrivateChat
from scheduler import run_immediate_check, run_immediate_sync

from db import DonationDB
from datetime import datetime


router = Router()

def is_admin(user_id: int) -> bool:
    admin_ids_str = config("ADMIN_IDS", default="")

    if not admin_ids_str:
        return False
    
    try: 
        admin_ids = [int(id.strip()) for id in admin_ids_str.split(",")]
        return user_id in admin_ids
    except ValueError:
        print(f"Ошибка: некорректный формат ADMIN_IDS в .env")
        return False

@router.message(IsPrivateChat(), F.text == "/start")
async def admin_menu(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав администратора")
        return
    
    text = (
        "<b>Панель администратора</b>\n\n"
        "Доступные команды:\n\n"
        "/stats - Статистика базы данных\n"
        "/sync - Синхронизировать донаты\n"
        "/check - Проверить подписки\n"
        "/user [username] - Информация о пользователе\n"
        "/admin - Показать это меню"
    )
    
    await message.answer(text)

@router.message(IsPrivateChat(), F.text == "/stats")
async def admin_stats(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав администратора")
        return

    db = DonationDB()
    try:
        all_donations = db.get_all_donations()
        
        total_donations = len(all_donations)
        total_amount = sum(d[2] for d in all_donations)
        
        current_time = datetime.now().isoformat()
        active_subs = sum(1 for d in all_donations if d[4] and d[4] > current_time)
        expired_subs = total_donations - active_subs
        
        text = (
            "<b>Статистика базы данных</b>\n\n"
            f"Всего пользователей: <b>{total_donations}</b>\n"
            f"Общая сумма донатов: <b>{total_amount:.2f} руб.</b>\n"
            f"Активных подписок: <b>{active_subs}</b>\n"
            f"Истекших подписок: <b>{expired_subs}</b>\n"
            f"Средний донат: <b>{total_amount/total_donations:.2f} руб.</b>" if total_donations > 0 else ""
        )
        
        await message.answer(text)
    except Exception as e:
        await message.answer(f"Ошибка при получении статистики: {e}")
    finally:
        db.close()

@router.message(IsPrivateChat(), F.text == "/sync")
async def admin_sync_donations(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав администратора")
        return
    
    ACCESS_TOKEN = config("ACCESS_TOKEN")
    
    await message.answer("Запуск синхронизации донатов...")
    
    try:
        stats = await run_immediate_sync(ACCESS_TOKEN)
        if stats:
            text = (
                "<b>Синхронизация завершена</b>\n\n"
                f"Всего обработано: <b>{stats['total']}</b>\n"
                f"Добавлено новых: <b>{stats['inserted']}</b>\n"
                f"Обновлено: <b>{stats['updated']}</b>\n"
                f"Ошибок: <b>{stats['failed']}</b>"
            )
        else:
            text = "Новых донатов не найдено"
        await message.answer(text)
    except Exception as e:
        await message.answer(f"Ошибка при синхронизации: {e}")

@router.message(IsPrivateChat(), F.text == "/check")
async def admin_check_subscriptions(message: Message):
    CHANNEL_ID = config("CHANNEL_ID")

    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)

    if member.status not in ["creator", "administrator"]:
        await message.answer("Эта команда доступна только администраторам")
        return
    
    await message.answer("Запуск проверки подписок...")
    
    try:
        await run_immediate_check(message.bot, CHANNEL_ID)
        await message.answer("Проверка подписок завершена")
    except Exception as e:
        await message.answer(f"Ошибка при проверке: {e}")

@router.message(IsPrivateChat(), Command("user"))
async def admin_user_info(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав администратора")
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /user username\nПример: /user johndoe")
        return
    
    username = parts[1].strip().lstrip('@')
    
    from db import user_donations
    
    try:
        stats = user_donations(username)
        
        if not stats or len(stats) == 0:
            await message.answer(f"Пользователь @{username} не найден в базе данных")
            return
        
        stat = stats[0]
        amount = stat[0]
        last_date = stat[1]
        sub_date = stat[2]
        
        from datetime import datetime
        current_time = datetime.now()
        
        if sub_date:
            sub_datetime = datetime.fromisoformat(sub_date.replace('Z', '+00:00'))
            is_active = sub_datetime > current_time
            status = "Активна" if is_active else "Истекла"
            
            if is_active:
                days_left = (sub_datetime - current_time).days
                status += f" (осталось {days_left} дней)"
        else:
            status = "Не определена"
        
        text = (
            f"<b>Информация о пользователе @{username}</b>\n\n"
            f"Сумма донатов: <b>{amount} руб.</b>\n"
            f"Последний донат: <b>{last_date}</b>\n"
            f"Подписка до: <b>{sub_date}</b>\n"
            f"Статус: {status}"
        )
        
        await message.answer(text)
    except Exception as e:
        await message.answer(f"Ошибка при получении информации: {e}")