from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        [
            KeyboardButton(text="Старт"), 
            KeyboardButton(text="Баланс"), 
            KeyboardButton(text="Сброс")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )
