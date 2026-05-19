"""Отправка уведомлений пользователям через Telegram-бота.

Эти функции вызываются из API-слоя и планировщика опросов. Если токен
бота не задан, send_message() тихо возвращает False.
"""
import html
import logging
from typing import Optional

from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardMarkup

from database.models import UserRoleEnum
from services.bot.instance import get_bot
from services.bot.keyboards import poll_reply_keyboard

logger = logging.getLogger(__name__)

ROLE_NAMES = {
    UserRoleEnum.PROJECT_MANAGER: "Проектник",
    UserRoleEnum.MAIN_ORGANIZER: "Главный организатор",
    UserRoleEnum.RESPONSIBLE: "Ответственный",
    UserRoleEnum.WORKER: "Работник",
}


async def send_message(
    telegram_id: int,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> bool:
    """Отправить сообщение пользователю в Telegram. Возвращает True при успехе."""
    if not telegram_id:
        return False
    bot = get_bot()
    if bot is None:
        logger.warning("TELEGRAM_BOT_TOKEN не задан — сообщение не отправлено")
        return False
    try:
        await bot.send_message(chat_id=telegram_id, text=text, reply_markup=reply_markup)
        return True
    except TelegramAPIError as e:
        logger.warning("Telegram: не удалось отправить сообщение (chat_id=%s): %s", telegram_id, e)
        return False


async def notify_role_assigned(
    telegram_id: int,
    role_name: str,
    is_new: bool = False,
    has_web_access: bool = False,
) -> None:
    """Уведомить пользователя о назначении или смене роли."""
    if not telegram_id:
        return
    if is_new:
        text = f"🎉 Вас добавили в систему!\n\nВаша роль: <b>{html.escape(role_name)}</b>\n\n"
    else:
        text = f"📋 Ваша роль изменена.\n\nНовая роль: <b>{html.escape(role_name)}</b>\n\n"
    if has_web_access:
        text += "У вас есть доступ к веб-интерфейсу. Обратитесь к администратору за логином и паролем."
    else:
        text += "Вы будете получать задачи через этого бота."
    await send_message(telegram_id, text)


async def notify_task_assigned(telegram_id: int, task_title: str, task_description: str = "") -> None:
    """Уведомить пользователя о назначенной ему задаче."""
    if not telegram_id:
        return
    desc = (task_description or "").strip()
    if len(desc) > 200:
        desc = desc[:200] + "..."
    text = f"📌 <b>Вам назначена задача</b>\n\n<b>{html.escape(task_title or '')}</b>\n"
    if desc:
        text += f"\n{html.escape(desc)}\n"
    text += "\nПросмотрите задачу в боте или веб-интерфейсе."
    await send_message(telegram_id, text)


async def notify_task_poll(telegram_id: int, task_title: str, task_id: int) -> None:
    """Напоминание-опрос о задаче с inline-кнопкой «Ответить»."""
    if not telegram_id:
        return
    text = (
        f"📋 <b>Напоминание о задаче</b>\n\n"
        f"<b>{html.escape(task_title or '')}</b>\n\n"
        f"Как продвигается выполнение? Нажмите кнопку ниже "
        f"или обновите статус в веб-интерфейсе."
    )
    await send_message(telegram_id, text, reply_markup=poll_reply_keyboard(task_id))
