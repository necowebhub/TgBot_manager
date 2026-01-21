from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from decouple import config
from filters.chat_type import isChannelChat
from scheduler import run_immediate_check

router = Router()

@router.message(isChannelChat(), Command("check_subscriptions"))
async def manual_subscription_check(message: Message):
    CHANNEL_ID = config("CHANNEL_ID")

    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)

    if member.status not in ["creator", "administrator"]:
        await message.answer("⛔ Эта команда доступна только администраторам")
        return
    
    await message.answer("🔄 Запуск проверки подписок...")
    
    try:
        await run_immediate_check(message.bot, CHANNEL_ID)
        await message.answer("✅ Проверка подписок завершена")
    except Exception as e:
        await message.answer(f"❌ Ошибка при проверке: {e}")