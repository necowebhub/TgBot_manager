import asyncio
import re
from datetime import datetime
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from db import get_expired_users


async def extract_username_from_message(message_text):
    if not message_text:
        return None
    
    mention_match = re.search(r'@(\w+)', message_text)
    if mention_match:
        return mention_match.group(1)
    
    words = message_text.split()
    for word in words:
        if len(word) > 3 and word.isalnum():
            return word
    
    return None


async def check_and_remove_expired_subscriptions(bot: Bot, channel_id: str):
    print(f"[{datetime.now()}] Начало проверки подписок...")
    
    expired_users = get_expired_users()
    
    if not expired_users:
        print("Нет пользователей с истекшей подпиской")
        return
    
    print(f"Найдено {len(expired_users)} записей с истекшей подпиской")
    
    removed_count = 0
    error_count = 0
    
    for user_id, message_text, sub_date in expired_users:
        username = await extract_username_from_message(message_text)
        
        if not username:
            print(f"Не удалось извлечь username из сообщения: {message_text}")
            error_count += 1
            continue
        
        try:
            chat_member = await bot.get_chat_member(channel_id, f"@{username}")
            user_id_to_ban = chat_member.user.id
            
            await bot.ban_chat_member(channel_id, user_id_to_ban)
            
            print(f"✓ Пользователь @{username} удален из канала (подписка до {sub_date})")
            removed_count += 1
            
        except TelegramBadRequest as e:
            if "user not found" in str(e).lower():
                print(f"✗ Пользователь @{username} не найден в канале")
            elif "not enough rights" in str(e).lower():
                print(f"✗ Недостаточно прав для удаления @{username}")
            else:
                print(f"✗ Ошибка при удалении @{username}: {e}")
            error_count += 1
            
        except Exception as e:
            print(f"✗ Неожиданная ошибка при обработке @{username}: {e}")
            error_count += 1
        
        await asyncio.sleep(0.5)
    
    print(f"\n=== Результаты проверки ===")
    print(f"Проверено записей: {len(expired_users)}")
    print(f"Удалено пользователей: {removed_count}")
    print(f"Ошибок: {error_count}")
    print(f"[{datetime.now()}] Проверка завершена\n")