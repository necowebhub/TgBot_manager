from aiogram import Router, F
from aiogram.types import Message

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
        return text
    
    await message.answer(text, reply_markup=get_main_keyboard())



@router.message(IsPrivateChat(), F.text == "Приватка")
async def start_fund(message: Message):
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

    stat = user_donations(username)
    if not stat:
        text = (
            "Донаты не найдены. Убедитесь, что ваш ник указан в сообщении доната."
        )
        await message.answer(text, reply_markup=get_main_keyboard())
        return

    text = f'Username: "{username}"\n'
    text += f'Сумма донатов: {stat['amount']}\n'
    text += f'Дата последнего доната: {stat['date']}\n'
    text += f'Подписка действует до: {stat['sub']}'

    await message.answer(text, reply_markup=get_main_keyboard())

@router.message(IsPrivateChat(), F.text == "Донат")
async def donate_url(message: Message):
    await message.answer("Нажмите кнопку:", reply_markup=get_donate_button())

@router.message(IsPrivateChat())
async def echo_handler(message: Message):
    await message.answer(
        "Неизвестная команда. Используйте кнопки или вручную наберите:\n"
        "- 'Приватка' для получения ссылки-приглашения\n"
        "- 'Я' для проверки статуса подписки\n"
        "- 'Донат' для продления подписки",
        reply_markup=get_main_keyboard()
    )
