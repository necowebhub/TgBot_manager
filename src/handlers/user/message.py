from aiogram import Router, F
from aiogram.types import Message
from datetime import datetime

from filters.chat_type import IsPrivateChat
from keyboards.user import get_main_keyboard, get_donate_button

from db import user_donations
from logger_config import setup_logger

logger = setup_logger(__name__)
router = Router()

def validate_username(username: str) -> bool:
    if not username:
        return False
    import re
    return bool(re.match(r'^[a-zA-Z0-9_]{5,32}$', username))

@router.message(IsPrivateChat(), F.text == "/start")
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    
    logger.info(f"Пользователь {user_id} (@{username}) запустил бота")
    
    text = (
        "Привет! Я бот для управления подпиской на тг канал стримера Brainnfuq.\n\n"
        "Функционал:\n"
        "- Нажмите кнопку 'Приватка' чтобы получить ссылку приглашение, если ваша подписка оплачена.\n"
        "- 'Я' — узнать статус подписки и оставшийся период.\n"
        "- 'Донат' — приобрести подписку или увеличить срок активной. Каждые 200 рублей продлевают срок подписки на 1 месяц.\n\n"
        "Если вы оплатили подписку но не можете получить доступ: подождите, списки обновляются каждый час.\n"
        "По поводу всех вопросов писать разработчику: @necoweb"
    )

    if not username:
        logger.warning(f"Пользователь {user_id} не имеет username")
        text += (
            "\n\nУ вас не установлен username в Telegram.\n"
            "Пожалуйста, установите username в настройках Telegram."
        )
        await message.answer(text)
        return text
    
    if not validate_username(username):
        logger.warning(f"Пользователь {user_id} имеет невалидный username: {username}")
        text += (
            "\n\nВаш username содержит недопустимые символы.\n"
            "Username должен содержать только буквы, цифры и подчёркивание."
        )
        await message.answer(text)
        return
    
    await message.answer(text, reply_markup=get_main_keyboard())

@router.message(IsPrivateChat(), F.text == "Приватка")
async def get_invite_link(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username

    logger.info(f"Пользователь {user_id} (@{username}) запросил ссылку-приглашение")

    if not username:
        logger.warning(f"Пользователь {user_id} без username запросил приватку")
        text = (
            "У вас не установлен username в Telegram.\n"
            "Пожалуйста, установите username в настройках Telegram."
        )
        await message.answer(text, reply_markup=get_main_keyboard())
        return
    
    if not validate_username(username):
        logger.warning(f"Пользователь {user_id} с невалидным username запросил приватку: {username}")
        text = (
            "⚠️ Ваш username содержит недопустимые символы.\n"
            "Username должен содержать только буквы, цифры и подчёркивание."
        )
        await message.answer(text, reply_markup=get_main_keyboard())
        return
    
    try:
        donations = user_donations(username)
    except Exception as e:
        logger.error(f"Ошибка при получении донатов для @{username}: {e}", exc_info=True)
        text = f"Ошибка при получении данных: {str(e)}\nОбратитесь к администратору @necoweb"
        await message.answer(text, reply_markup=get_main_keyboard())
        return

    if not donations:
        logger.info(f"Донаты не найдены для @{username}")
        text = (
            "Донаты не найдены. Убедитесь, что ваш ник указан в сообщении доната.\n\n"
            "Для получения доступа к приватному каналу необходимо сделать донат "
            "с указанием вашего username в сообщении."
        )
        await message.answer(text, reply_markup=get_main_keyboard())
        return

    donation_data = donations[0]
    amount = donation_data[0]
    last_date = donation_data[1]
    sub_date_str = donation_data[2]

    try:
        sub_date = datetime.fromisoformat(sub_date_str.replace('Z', '+00:00'))
        current_date = datetime.now(sub_date.tzinfo) if sub_date.tzinfo else datetime.now()

        if current_date > sub_date:
            logger.info(f"Подписка истекла для @{username} ({sub_date})")
            text = (
                f"Ваша подписка истекла {sub_date.strftime('%d.%m.%Y')}.\n\n"
                f"Общая сумма донатов: {amount} руб.\n"
                f"Последний донат: {last_date}\n\n"
                "Для продления подписки нажмите кнопку 'Донат'.\n"
                "Каждые 200 рублей продлевают подписку на 1 месяц."
            )
            await message.answer(text, reply_markup=get_main_keyboard())
            return
    
    except (ValueError, AttributeError) as e:
        logger.error(f"Ошибка парсинга даты для @{username}: {e}", exc_info=True)
        text = "Ошибка при проверке даты подписки. Обратитесь к разработчику."
        await message.answer(text, reply_markup=get_main_keyboard())
        return

    try:
        from decouple import config
        CHANNEL_ID = config("CHANNEL_ID")

        invite_link = await message.bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            member_limit=1,
            name=f'Invite for @{username}'
        )

        logger.info(f"Создана ссылка-приглашение для @{username}")
        
        text = (
            f"Ваша подписка активна до {sub_date.strftime('%d.%m.%Y')}!\n\n"
            f"Вот ваша персональная ссылка-приглашение в канал:\n"
            f"{invite_link.invite_link}\n\n"
            f"Ссылка действительна для одного использования.\n"
            f"После перехода по ссылке она станет недействительной.\n\n"
            f"Общая сумма донатов: {amount} руб."
        )

    except Exception as e:
        logger.error(f"Ошибка создания ссылки для @{username}: {e}", exc_info=True)
        text = (
            f"Ошибка при создании ссылки-приглашения: {str(e)}\n\n"
            "Обратитесь к администратору @necoweb"
        )

    await message.answer(text, reply_markup=get_main_keyboard())

@router.message(IsPrivateChat(), F.text == "Я")
async def show_balance(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    
    logger.info(f"Пользователь {user_id} (@{username}) проверяет статус подписки")
    
    if not username:
        logger.warning(f"Пользователь {user_id} без username проверяет статус")
        text = (
            "У вас не установлен username в Telegram.\n"
            "Пожалуйста, установите username в настройках Telegram."
        )
        await message.answer(text, reply_markup=get_main_keyboard())
        return
    
    if not validate_username(username):
        logger.warning(f"Пользователь {user_id} с невалидным username проверяет статус: {username}")
        text = (
            "Ваш username содержит недопустимые символы."
        )
        await message.answer(text, reply_markup=get_main_keyboard())
        return

    try:
        donations = user_donations(username)
    except Exception as e:
        logger.error(f"Ошибка при получении донатов для @{username}: {e}", exc_info=True)
        text = f"Ошибка при получении данных: {str(e)}"
        await message.answer(text, reply_markup=get_main_keyboard())
        return

    if not donations:
        logger.info(f"Донаты не найдены для @{username}")
        text = (
            "Донаты не найдены. Убедитесь, что ваш ник указан в сообщении доната."
        )
        await message.answer(text, reply_markup=get_main_keyboard())
        return

    donation_data = donations[0]
    amount = donation_data[0]
    last_date = donation_data[1]
    sub_date_str = donation_data[2]

    try:
        sub_date = datetime.fromisoformat(sub_date_str.replace('Z', '+00:00'))
        current_date = datetime.now(sub_date.tzinfo) if sub_date.tzinfo else datetime.now()

        if current_date > sub_date:
            status = "Истекла"
            status_emoji = "🔴"
        else:
            days_left = (sub_date - current_date).days
            status = f"Активна (осталось {days_left} дней)"
            status_emoji = "🟢"

    except Exception as e:
        logger.error(f"Ошибка парсинга даты для @{username}: {e}", exc_info=True)
        status = "Ошибка определения статуса"
        status_emoji = "⚠️"
        sub_date_str = "Ошибка определения даты"

    logger.info(f"Статус подписки для @{username}: {status}")
    
    text = (
        f"{status_emoji} <b>Статус подписки</b>\n\n"
        f'Username: @{username}\n'
        f'Сумма донатов: {amount} руб.\n'
        f'Дата последнего доната: {last_date}\n'
        f'Подписка действует до: {sub_date_str}\n'
        f'Статус: {status}\n'
    )

    await message.answer(text, reply_markup=get_main_keyboard())

@router.message(IsPrivateChat(), F.text == "Донат")
async def donate_url(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    
    logger.info(f"Пользователь {user_id} (@{username}) запросил информацию о донате")
    
    if not username:
        logger.warning(f"Пользователь {user_id} без username запросил донат")
        text = (
            "У вас не установлен username в Telegram.\n"
            "Пожалуйста, установите username в настройках Telegram, "
            "иначе мы не сможем идентифицировать ваш донат.\n\n"
            "После установки username укажите его в сообщении доната."
        )
        await message.answer(text, reply_markup=get_main_keyboard())
        return
    
    text = (
        f"<b>Оплата подписки</b>\n\n"
        f"ВАЖНО: В сообщении доната обязательно укажите ваш username: @{username}\n\n"
        f"Тарифы:\n"
        f"• 200 руб = 1 месяц\n"
        f"• 400 руб = 2 месяца\n"
        f"• 600 руб = 3 месяца\n\n"
        f"После оплаты подождите до 1 часа для обновления базы данных.\n\n"
        f"Нажмите кнопку ниже для перехода к оплате:"
    )

    await message.answer(text, reply_markup=get_donate_button())

@router.message(IsPrivateChat())
async def echo_handler(message: Message):
    user_id = message.from_user.id
    logger.debug(f"Неизвестная команда от пользователя {user_id}: {message.text}")
    
    await message.answer(
        "Неизвестная команда. Используйте кнопки или вручную наберите:\n"
        "- 'Приватка' для получения ссылки-приглашения\n"
        "- 'Я' для проверки статуса подписки\n"
        "- 'Донат' для продления подписки",
        reply_markup=get_main_keyboard()
    )
