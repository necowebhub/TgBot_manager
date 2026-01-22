import asyncio
import re
from datetime import datetime
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from db import get_expired_users
from logger_config import setup_logger

logger = setup_logger(__name__)


async def extract_username_from_message(message_text):
    if not message_text:
        return None
    
    mention_match = re.search(r'@(\w+)', message_text)
    if mention_match:
        return mention_match.group(1)
    
    patterns = [
        r'(?:username|user|ник|имя пользователя)[\s:=]+(@?\w+)',
        r'(?:telegram|tg)[\s:=]+(@?\w+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, message_text, re.IGNORECASE)
        if match:
            username = match.group(1).lstrip('@')
            if len(username) >= 5 and username.replace('_', '').isalnum():
                return username
    
    words = message_text.split()
    for word in words:
        clean_word = word.strip('.,!?;:()[]{}"\' ').lstrip('@')

        if (5 <= len(clean_word) <= 32 and clean_word.replace('_', '').isalnum() and not clean_word.isdigit() and re.match(r'^[a-zA-Z0-9_]+$', clean_word)):
            return clean_word
    
    return None


async def check_and_remove_expired_subscriptions(bot: Bot, channel_id: str):
    logger.info("Начало проверки истекших подписок...")
    
    expired_users = get_expired_users()
    
    if not expired_users:
        logger.info("Нет пользователей с истекшей подпиской")
        return
    
    logger.info(f"Найдено {len(expired_users)} записей с истекшей подпиской")
    
    removed_count = 0
    error_count = 0
    
    for user_id, message_text, sub_date in expired_users:
        username = await extract_username_from_message(message_text)
        
        if not username:
            logger.warning(f"Не удалось извлечь username из сообщения: {message_text[:100]}...")
            error_count += 1
            continue
        
        try:
            chat_member = await bot.get_chat_member(channel_id, f"@{username}")
            user_id_to_ban = chat_member.user.id
            
            await bot.ban_chat_member(channel_id, user_id_to_ban)
            
            logger.info(f"Пользователь @{username} удален из канала (подписка до {sub_date})")
            removed_count += 1
            
        except TelegramBadRequest as e:
            if "user not found" in str(e).lower():
                logger.warning(f"Пользователь @{username} не найден в канале")
            elif "not enough rights" in str(e).lower():
                logger.error(f"Недостаточно прав для удаления @{username}")
            else:
                logger.error(f"Ошибка при удалении @{username}: {e}")
            error_count += 1
            
        except Exception as e:
            logger.error(f"Неожиданная ошибка при обработке @{username}: {e}", exc_info=True)
            error_count += 1
        
        await asyncio.sleep(0.5)
    
    logger.info(
        f"Проверка завершена - "
        f"проверено: {len(expired_users)}, "
        f"удалено: {removed_count}, "
        f"ошибок: {error_count}"
    )
