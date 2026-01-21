from aiogram import Router, F
from aiogram.types import Message
from datetime import datetime

from filters.chat_type import IsPrivateChat
from keyboards.user import get_main_keyboard, get_donate_button

from ...db import user_donations

router = Router()

@router.message(IsPrivateChat(), F.text == "/start")
async def cmd_start(message: Message):
    text = (
        "Привет! Я бот для управления подпиской на тг канал стримера Brainnfuq.\n\n"
        "Функционал:\n"
        "- Нажмите кнопку 'Приватка' чтобы получить ссылку приглашение, если ваша подписка оплачена.\n"
        "- 'Я' — узнать статус подписки и оставшийся период.\n"
        "- 'Донат' — приобрести подписку или увеличить срок активной. Каждые 200 рублей продлевают срок подписки на 1 месяц.\n\n"
        "Если вы оплатили подписку но не можете получить доступ: подождите, списки обновляются каждый час.\n"
        "По поводу всех вопросов писать разработчику: @necoweb"
    )

    username = message.from_user.username
    if not username:
        text += (
            "\n\nУ вас не установлен username в Telegram.\n"
            "Пожалуйста, установите username в настройках Telegram."
        )
        await message.answer(text)
        return text
    
    await message.answer(text, reply_markup=get_main_keyboard())

@router.message(IsPrivateChat(), F.text == "Приватка")
async def get_invite_link(message: Message):
    username = message.from_user.username

    if not username:
        text = (
            "У вас не установлен username в Telegram.\n"
            "Пожалуйста, установите username в настройках Telegram."
        )
        await message.answer(text, reply_markup=get_main_keyboard())
        return
    
    donations = user_donations(username)

    if not donations:
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
        current_date = datetime.now(sub_date.tzinfo)

        if current_date > sub_date:
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

        text = (
            f"Ваша подписка активна до {sub_date.strftime('%d.%m.%Y')}!\n\n"
            f"Вот ваша персональная ссылка-приглашение в канал:\n"
            f"{invite_link.invite_link}\n\n"
            f"Ссылка действительна для одного использования.\n"
            f"После перехода по ссылке она станет недействительной.\n\n"
            f"Общая сумма донатов: {amount} руб."
        )

    except Exception as e:
        text = (
            f"Ошибка при создании ссылки-приглашения: {str(e)}\n\n"
            "Обратитесь к администратору @necoweb"
        )

    await message.answer(text, reply_markup=get_main_keyboard())

@router.message(IsPrivateChat(), F.text == "Я")
async def show_balance(message: Message):
    username = message.from_user.username
    if not username:
        text = (
            "У вас не установлен username в Telegram.\n"
            "Пожалуйста, установите username в настройках Telegram."
        )
        await message.answer(text, reply_markup=get_main_keyboard())
        return

    donations = user_donations(username)
    if not donations:
        text = (
            "Донаты не найдены. Убедитесь, что ваш ник указан в сообщении доната."
        )
        await message.answer(text, reply_markup=get_main_keyboard())
        return

    # Берем первую запись
    donation_data = donations[0]
    amount = donation_data[0]
    last_date = donation_data[1]
    sub_date_str = donation_data[2]

    try:
        sub_date = datetime.fromisoformat(sub_date_str.replace('Z', '+00:00'))
        current_date = datetime.now(sub_date.tzinfo)

        if current_date > sub_date:
            status = "Истекла"
        else:
            days_left = (sub_date - current_date).days
            status = f"Активна (осталось {days_left} дней)"

    except:
        status = "Неизвестно"
        sub_date_str = "Ошибка определения даты"

    text = (
        f'Username: @{username}\n'
        f'Сумма донатов: {amount} руб.\n'
        f'Дата последнего доната: {last_date}\n'
        f'Подписка действует до: {sub_date_str}\n'
        f'Статус: {status}\n'
    )

    await message.answer(text, reply_markup=get_main_keyboard())

@router.message(IsPrivateChat(), F.text == "Донат")
async def donate_url(message: Message):
    username = message.from_user.username
    
    if not username:
        text = (
            "У вас не установлен username в Telegram.\n"
            "Пожалуйста, установите username в настройках Telegram, "
            "иначе мы не сможем идентифицировать ваш донат.\n\n"
            "После установки username укажите его в сообщении доната."
        )
        await message.answer(text, reply_markup=get_main_keyboard())
        return
    
    text = (
        f"Для оплаты подписки нажмите кнопку ниже.\n\n"
        f"ВАЖНО: В сообщении доната обязательно укажите ваш username: @{username}\n\n"
        f"Каждые 200 рублей = 1 месяц подписки\n"
        f"Например:\n"
        f"• 200 руб = 1 месяц\n"
        f"• 400 руб = 2 месяца\n"
        f"• 600 руб = 3 месяца\n\n"
        f"После оплаты подождите до 1 часа для обновления базы данных."
    )

    await message.answer(text, reply_markup=get_donate_button())

@router.message(IsPrivateChat())
async def echo_handler(message: Message):
    await message.answer(
        "Неизвестная команда. Используйте кнопки или вручную наберите:\n"
        "- 'Приватка' для получения ссылки-приглашения\n"
        "- 'Я' для проверки статуса подписки\n"
        "- 'Донат' для продления подписки",
        reply_markup=get_main_keyboard()
    )
