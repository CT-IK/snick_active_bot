"""CallbackData-фабрики для inline-кнопок бота.

aiogram упаковывает поля в строку callback_data (лимит Telegram — 64 байта).
"""
from aiogram.filters.callback_data import CallbackData


class PollAnswer(CallbackData, prefix="poll"):
    """Кнопка «Ответить» под сообщением-напоминанием о задаче."""

    task_id: int


class PollChoice(CallbackData, prefix="pollc"):
    """Выбор варианта ответа на опрос (готовый текст или «custom»)."""

    task_id: int
    value: str
