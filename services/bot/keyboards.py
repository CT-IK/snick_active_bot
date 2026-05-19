"""Inline-клавиатуры бота."""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.bot.callbacks import PollAnswer, PollChoice

# Готовые варианты ответа на опрос о задаче
POLL_CHOICES = ["В работе", "На проверке", "Готово"]
# Значение value для варианта «написать свой текст»
POLL_CUSTOM = "custom"


def poll_reply_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Кнопка «Ответить» под напоминанием о задаче."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Ответить", callback_data=PollAnswer(task_id=task_id))
    return builder.as_markup()


def poll_choice_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора ответа на опрос: готовые варианты + свой текст."""
    builder = InlineKeyboardBuilder()
    for choice in POLL_CHOICES:
        builder.button(
            text=choice,
            callback_data=PollChoice(task_id=task_id, value=choice),
        )
    builder.button(
        text="✍️ Напишу текст",
        callback_data=PollChoice(task_id=task_id, value=POLL_CUSTOM),
    )
    builder.adjust(2)
    return builder.as_markup()
