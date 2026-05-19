"""Telegram-бот на aiogram 3.x.

Публичный интерфейс пакета: запуск/остановка бота и функции уведомлений,
которые вызываются из API-слоя и планировщика опросов.
"""
from services.bot.runner import start_bot, stop_bot
from services.bot.notifications import (
    ROLE_NAMES,
    send_message,
    notify_role_assigned,
    notify_task_assigned,
    notify_task_poll,
)

__all__ = [
    "start_bot",
    "stop_bot",
    "ROLE_NAMES",
    "send_message",
    "notify_role_assigned",
    "notify_task_assigned",
    "notify_task_poll",
]
