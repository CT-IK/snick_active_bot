"""Сервис уведомлений в Telegram"""
import logging
from typing import Optional

from config import TELEGRAM_BOT_TOKEN
from database.models import UserRoleEnum

logger = logging.getLogger(__name__)

ROLE_NAMES = {
    UserRoleEnum.PROJECT_MANAGER: "Проектник",
    UserRoleEnum.MAIN_ORGANIZER: "Главный организатор",
    UserRoleEnum.RESPONSIBLE: "Ответственный",
    UserRoleEnum.WORKER: "Работник",
}


async def send_telegram_message(telegram_id: int, text: str, reply_markup: Optional[dict] = None) -> bool:
    """Отправить сообщение пользователю в Telegram (опционально с inline-кнопками)."""
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN не задан, уведомление не отправлено")
        return False
    try:
        import httpx
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": telegram_id,
            "text": text,
            "parse_mode": "HTML",
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=10.0)
            if resp.status_code != 200:
                try:
                    err = resp.json()
                    desc = err.get("description", resp.text)
                except Exception:
                    desc = resp.text
                logger.warning("Telegram API error %s: %s", resp.status_code, desc)
                return False
            return True
    except Exception as e:
        logger.exception("Ошибка отправки в Telegram: %s", e)
        return False


async def notify_role_assigned(telegram_id: int, role_name: str, is_new: bool = False, has_web_access: bool = False):
    """Уведомить пользователя о назначении роли"""
    if not telegram_id:
        logger.debug("notify_role_assigned: пропуск, telegram_id пустой")
        return
    if is_new:
        text = f"🎉 Вас добавили в систему!\n\nВаша роль: <b>{role_name}</b>\n\n"
    else:
        text = f"📋 Ваша роль изменена.\n\nНовая роль: <b>{role_name}</b>\n\n"
    if has_web_access:
        text += "У вас есть доступ к веб-интерфейсу. Обратитесь к администратору за логином и паролем."
    else:
        text += "Вы получите задачи через этого бота."
    ok = await send_telegram_message(telegram_id, text)
    if not ok:
        logger.warning("Не удалось отправить уведомление о роли в Telegram (chat_id=%s)", telegram_id)


async def notify_task_assigned(telegram_id: int, task_title: str, task_description: str = ""):
    """Уведомить пользователя о назначении задачи"""
    desc = (task_description or "").strip()[:200]
    if len((task_description or "").strip()) > 200:
        desc += "..."
    text = f"📌 <b>Вам назначена задача</b>\n\n<b>{task_title}</b>\n"
    if desc:
        text += f"\n{desc}\n"
    text += "\nПросмотрите задачу в боте или веб-интерфейсе."
    await send_telegram_message(telegram_id, text)


def _poll_reply_keyboard(task_id: int) -> dict:
    """Inline-кнопка «Ответить» для сообщения-опроса (callback_data до 64 байт)."""
    return {
        "inline_keyboard": [
            [{"text": "📝 Ответить", "callback_data": f"poll:{task_id}"}]
        ]
    }


async def notify_task_poll(telegram_id: int, task_title: str, task_id: int):
    """Напоминание-опрос: как продвигается задача, с кнопкой «Ответить»."""
    text = (
        f"📋 <b>Напоминание о задаче</b>\n\n"
        f"<b>{task_title}</b>\n\n"
        f"Как продвигается выполнение? Нажмите кнопку ниже или обновите статус в веб-интерфейсе."
    )
    await send_telegram_message(telegram_id, text, reply_markup=_poll_reply_keyboard(task_id))
