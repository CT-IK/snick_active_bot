"""Обработка обновлений Telegram-бота: кнопка «Ответить» на опросе и сохранение ответа."""
import asyncio
import logging
from typing import Optional

import httpx
from sqlalchemy import select

from config import TELEGRAM_BOT_TOKEN
from database.database import AsyncSessionLocal
from database.models import TaskPollResponse, TaskStatusEnum
from dao.user_dao import UserDAO
from dao.task_dao import TaskDAO

logger = logging.getLogger(__name__)

# Состояние: ждём текстовый ответ от пользователя. Ключ = chat_id, значение = (task_id, telegram_id)
_poll_wait_state: dict[int, tuple[int, int]] = {}

# Максимальная длина callback_data в Telegram — 64 байта
POLLR_PREFIX = "pollr:"
POLLR_CUSTOM = "custom"


def _reply_keyboard_choose(task_id: int) -> dict:
    """Клавиатура выбора ответа на опрос."""
    return {
        "inline_keyboard": [
            [
                {"text": "В работе", "callback_data": f"pollr:{task_id}:В работе"},
                {"text": "На проверке", "callback_data": f"pollr:{task_id}:На проверке"},
            ],
            [
                {"text": "Готово", "callback_data": f"pollr:{task_id}:Готово"},
                {"text": "Напишу текст", "callback_data": f"pollr:{task_id}:{POLLR_CUSTOM}"},
            ],
        ]
    }


async def _save_poll_response(telegram_id: int, task_id: int, response_text: str) -> bool:
    """Сохранить ответ на опрос в БД по telegram_id и task_id."""
    async with AsyncSessionLocal() as db:
        user = await UserDAO.get_by_telegram_id(db, telegram_id)
        if not user:
            return False
        result = await db.execute(
            select(TaskPollResponse)
            .where(
                TaskPollResponse.task_id == task_id,
                TaskPollResponse.user_id == user.id,
                TaskPollResponse.response_text.is_(None),
            )
            .order_by(TaskPollResponse.polled_at.desc())
            .limit(1)
        )
        rec = result.scalar_one_or_none()
        if rec:
            rec.response_text = (response_text or "").strip() or None
            # Продвинуть статус задачи вправо по этапу при ответе в боте
            task = await TaskDAO.get_by_id(db, task_id)
            if task and task.status not in (TaskStatusEnum.DONE, TaskStatusEnum.CANCELLED):
                next_status = {
                    TaskStatusEnum.NEW: TaskStatusEnum.IN_PROGRESS,
                    TaskStatusEnum.IN_PROGRESS: TaskStatusEnum.REVIEW,
                    TaskStatusEnum.REVIEW: TaskStatusEnum.DONE,
                }.get(task.status)
                if next_status:
                    task.status = next_status
            await db.commit()
            return True
    return False


async def _bot_request(method: str, request_timeout: float = 15.0, **kwargs) -> Optional[dict]:
    """Вызов метода Telegram Bot API. Для getUpdates передайте request_timeout > 30 (long poll)."""
    if not TELEGRAM_BOT_TOKEN:
        return None
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(url, json=kwargs, timeout=request_timeout)
            if r.status_code != 200:
                logger.warning("Telegram API %s: %s %s", method, r.status_code, r.text)
                return None
            return r.json()
    except httpx.ReadTimeout:
        # Ожидаемо для getUpdates при long polling — просто повторяем запрос
        if method != "getUpdates":
            logger.warning("Telegram API %s: ReadTimeout", method)
        return None
    except Exception as e:
        logger.exception("Telegram API %s: %s", method, e)
        return None


async def _send_message(chat_id: int, text: str, reply_markup: Optional[dict] = None) -> bool:
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    result = await _bot_request("sendMessage", **payload)
    return result is not None and result.get("ok")


async def _answer_callback(callback_query_id: str, text: Optional[str] = None) -> None:
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text[:200]
    await _bot_request("answerCallbackQuery", **payload)


async def _handle_callback(data: str, chat_id: int, from_telegram_id: int, callback_query_id: str) -> None:
    """Обработка нажатия inline-кнопки."""
    # Нажали «Ответить» — показать выбор
    if data.startswith("poll:"):
        try:
            task_id = int(data.split(":", 1)[1])
        except (IndexError, ValueError):
            await _answer_callback(callback_query_id, "Ошибка")
            return
        await _answer_callback(callback_query_id)
        await _send_message(
            chat_id,
            "Как продвигается задача? Выберите или нажмите «Напишу текст»:",
            reply_markup=_reply_keyboard_choose(task_id),
        )
        return

    # Нажали один из вариантов ответа
    if data.startswith(POLLR_PREFIX):
        parts = data.split(":", 2)
        if len(parts) < 3:
            await _answer_callback(callback_query_id, "Ошибка")
            return
        try:
            task_id = int(parts[1])
        except ValueError:
            await _answer_callback(callback_query_id, "Ошибка")
            return
        label = parts[2]

        if label == POLLR_CUSTOM:
            await _answer_callback(callback_query_id)
            _poll_wait_state[chat_id] = (task_id, from_telegram_id)
            await _send_message(chat_id, "Напишите ваш ответ одним сообщением:")
            return

        # Готовый вариант
        ok = await _save_poll_response(from_telegram_id, task_id, label)
        await _answer_callback(callback_query_id, "Спасибо, ответ сохранён!" if ok else "Ответ уже был сохранён")
        if ok:
            await _send_message(chat_id, "✅ Ответ сохранён. Админ увидит его в таймлайне задачи.")


async def _handle_message(chat_id: int, from_telegram_id: int, text: str) -> None:
    """Обработка текстового сообщения (ответ на опрос)."""
    state = _poll_wait_state.get(chat_id)
    if not state:
        return
    task_id, telegram_id = state
    if from_telegram_id != telegram_id:
        return
    del _poll_wait_state[chat_id]
    text = (text or "").strip()
    if not text:
        await _send_message(chat_id, "Пустой ответ не сохранён.")
        return
    ok = await _save_poll_response(telegram_id, task_id, text)
    if ok:
        await _send_message(chat_id, "✅ Ответ сохранён. Админ увидит его в таймлайне задачи.")
    else:
        await _send_message(chat_id, "Не удалось сохранить (возможно, ответ уже был отправлен).")


async def _process_updates(updates: list) -> int:
    """Обработать список обновлений. Возвращает максимальный update_id."""
    last_id = 0
    for upd in updates:
        uid = upd.get("update_id", 0)
        if uid > last_id:
            last_id = uid

        if "callback_query" in upd:
            cq = upd["callback_query"]
            data = (cq.get("data") or "").strip()
            chat_id = cq.get("message", {}).get("chat", {}).get("id")
            from_id = cq.get("from", {}).get("id")
            if data and chat_id and from_id:
                await _handle_callback(data, chat_id, from_id, cq.get("id", ""))
            continue

        if "message" in upd:
            msg = upd["message"]
            chat_id = msg.get("chat", {}).get("id")
            from_user = msg.get("from") or {}
            from_id = from_user.get("id")
            text = (msg.get("text") or "").strip()
            if chat_id and from_id and text:
                await _handle_message(chat_id, from_id, text)

    return last_id


async def bot_updates_loop() -> None:
    """Бесконечный цикл long polling getUpdates."""
    if not TELEGRAM_BOT_TOKEN:
        logger.info("TELEGRAM_BOT_TOKEN не задан — бот опросов не запущен")
        return
    offset = 0
    while True:
        try:
            # timeout=30 — long poll у Telegram; HTTP-таймаут чуть больше (35 с)
            result = await _bot_request("getUpdates", request_timeout=35.0, offset=offset, timeout=30)
            if not result or not result.get("ok"):
                await asyncio.sleep(5)
                continue
            updates = result.get("result") or []
            if updates:
                offset = await _process_updates(updates) + 1
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception("Ошибка в bot_updates_loop: %s", e)
            await asyncio.sleep(10)
