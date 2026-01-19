from aiogram import Router, F
from aiogram.types import Message

from filters.chat_type import IsPrivateChat
from keyboards.user import get_main_keyboard


router = Router()

# Формат: (user_id: int, depositors: int, balance: int)
funds = []

@router.message(IsPrivateChat(), F.text == "/start")
async def cmd_start(message: Message):
    text = (
        "Привет! Я бот для управления страховым фондом.\n\n"
        "Функционал:\n"
        "- Нажмите кнопку 'Старт' для создания страхового фонда.\n"
        "- 'Баланс' — узнать текущий баланс вашего фонда.\n"
        "- 'Сброс' — расформировать фонд и получить выплаты.\n\n"
        "Чтобы добавить участников в фонд введите 'участников' и количество участников фонда. \n"
        "Чтобы обновить баланс фонда введите '+' или '-' и значение."
    )
    await message.answer(text, reply_markup=get_main_keyboard())

@router.message(IsPrivateChat(), F.text == "Старт")
async def start_fund(message: Message):
    user_id = message.from_user.id
    full_name = message.from_user.full_name

    # Проверяем, есть ли фонд у пользователя
    existing = next((f for f in funds if f[0] == user_id), None)

    if existing is None:
        # Добавляем новый фонд: (user_id, depositors=0, balance=0)
        funds.append((user_id, 0, 0))
        text = (
            f"Приветствуем! {full_name}\n\n"
            "Страховой фонд успешно создан!\n"
            "Баланс фонда: 0"
        )
    else:
        balance = existing[2]
        text = (
            f"Баланс вашего страхового фонда: {balance}.\n"
            "Чтобы создать новый фонд, необходимо расформировать старый, нажмите на кнопку сброса!"
        )

    await message.answer(text, reply_markup=get_main_keyboard())

@router.message(IsPrivateChat(), F.text == "Баланс")
async def show_balance(message: Message):
    user_id = message.from_user.id
    existing = next((f for f in funds if f[0] == user_id), None)

    if existing is None:
        text = "У вас пока нет страхового фонда. Нажмите кнопку 'Старт' для создания."
    else:
        balance = existing[2]
        text = f"Баланс фонда: {balance}"

    await message.answer(text, reply_markup=get_main_keyboard())

@router.message(IsPrivateChat(), F.text == "Сброс")
async def reset_fund(message: Message):
    user_id = message.from_user.id
    global funds

    existing = next((f for f in funds if f[0] == user_id), None)

    if existing is None:
        text = "У вас нет активного страхового фонда для сброса."
        await message.answer(text, reply_markup=get_main_keyboard())
        return

    _, depositors, balance = existing

    if depositors == 0:
        # Чтобы избежать деления на ноль
        payout = 0
        remainder = 0
    else:
        payout_per_depositor = balance // depositors
        
        if payout_per_depositor < 10:
            payout = 0
        elif payout_per_depositor // 1000 >= 1:
            payout = (payout_per_depositor // 1000) * 1000
        elif payout_per_depositor // 100 >= 1:
            payout = (payout_per_depositor // 100) * 100
        elif payout_per_depositor // 10 >= 1:
            payout = (payout_per_depositor // 10) * 10

        remainder = (balance - payout * depositors) + payout

    text = (
        "Страховой фонд расформирован!\n"
        f"Количество участников фонда: {depositors}\n"
        f"Баланс фонда: {balance}\n"
        f"Выплата: {payout}\n"
        f"Выплата основателю: {remainder}"
    )

    # Удаляем фонд из списка
    funds = [f for f in funds if f[0] != user_id]

    await message.answer(text, reply_markup=get_main_keyboard())

@router.message(IsPrivateChat())
async def update_fund_parameters(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()

    # Проверяем, есть ли фонд у пользователя
    idx = next((i for i, f in enumerate(funds) if f[0] == user_id), None)
    if idx is None:
        await message.answer(
            "У вас нет активного страхового фонда. Нажмите кнопку 'Старт' для создания.",
            reply_markup=get_main_keyboard()
        )
        return

    user_id_fund, depositors, balance = funds[idx]

    # Обработка изменения количества участников
    if text.lower().startswith("участников "):
        try:
            count_str = text[11:].strip()
            count = int(count_str)
            if count < 0:
                raise ValueError("Количество участников не может быть отрицательным.")
            # Обновляем количество участников
            funds[idx] = (user_id_fund, count, balance)
            await message.answer(
                f"Количество участников фонда обновлено: {count}",
                reply_markup=get_main_keyboard()
            )
        except ValueError:
            await message.answer(
                "Неверный формат количества участников. Используйте: участников N, где N — целое число.",
                reply_markup=get_main_keyboard()
            )
        return

    # Обработка изменения баланса
    if text.startswith("+") or text.startswith("-"):
        try:
            sign = 1 if text.startswith("+") else -1
            amount_str = text[1:].strip()
            amount = int(amount_str)
            if amount < 0:
                raise ValueError("Сумма должна быть положительным числом.")
            new_balance = balance + sign * amount
            if new_balance < 0:
                await message.answer(
                    "Баланс не может быть отрицательным.",
                    reply_markup=get_main_keyboard()
                )
                return
            if amount % 10 != 0:
                await message.answer(
                    "Число должно быть кратным 10."
                )
                return
            funds[idx] = (user_id_fund, depositors, new_balance)
            await message.answer(
                f"Баланс фонда обновлен: {new_balance}",
                reply_markup=get_main_keyboard()
            )
        except ValueError:
            await message.answer(
                "Неверный формат изменения баланса. Используйте: '+ X' или '- X', где X — целое число.",
                reply_markup=get_main_keyboard()
            )
        return

    # Если сообщение не подходит под указанные форматы, игнорируем или можно отправить подсказку
    await message.answer(
        "Неизвестная команда. Используйте:\n"
        "- 'участников N' для установки количества участников\n"
        "- '+ X' для увеличения баланса\n"
        "- '- X' для уменьшения баланса",
        reply_markup=get_main_keyboard()
    )
