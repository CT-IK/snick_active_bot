"""Планировщик опросов о задачах — отправка напоминаний в Telegram по расписанию"""
import asyncio
import logging
from datetime import datetime, timedelta
from database.database import AsyncSessionLocal
from database.models import Task, TaskStatusEnum, TaskPollResponse
from dao.task_dao import TaskDAO
from dao.user_dao import UserDAO
from services.telegram_notify import notify_task_poll

logger = logging.getLogger(__name__)


def _parse_time(s: str) -> tuple[int, int] | None:
    """Парсит 'HH:MM' в (час, минута)"""
    if not s or len(s.strip()) < 4:
        return None
    try:
        parts = s.strip().split(":")
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return None


async def _run_poll_check():
    """Проверить задачи и отправить опросы тем, кому пора"""
    now = datetime.utcnow()
    current_hour, current_min = now.hour, now.minute

    async with AsyncSessionLocal() as db:
        try:
            tasks = await TaskDAO.get_all(db, skip=0, limit=500)
        except Exception as e:
            logger.warning("Не удалось загрузить задачи для опроса: %s", e)
            return
        for task in tasks:
            if not task.poll_interval_days or not task.poll_time:
                continue
            if task.status in (TaskStatusEnum.DONE, TaskStatusEnum.CANCELLED):
                continue
            parsed = _parse_time(task.poll_time)
            if not parsed:
                continue
            poll_hour, poll_min = parsed
            if current_hour != poll_hour or current_min != poll_min:
                continue

            # Проверяем, прошло ли poll_interval_days с last_polled_at или created_at
            ref = task.last_polled_at or task.created_at
            if now - ref < timedelta(days=task.poll_interval_days):
                continue

            # Отправляем опрос всем исполнителям с telegram_id и создаём запись об опросе
            for user in task.assignees:
                if user.telegram_id:
                    try:
                        await notify_task_poll(user.telegram_id, task.title, task.id)
                        poll_rec = TaskPollResponse(
                            task_id=task.id,
                            user_id=user.id,
                            polled_at=now,
                            response_text=None,
                            status_at_poll=task.status.value if task.status else None,
                        )
                        db.add(poll_rec)
                    except Exception as e:
                        logger.exception("Ошибка отправки опроса: %s", e)

            task.last_polled_at = now
        await db.commit()


async def poll_scheduler_loop():
    """Фоновый цикл: каждую минуту проверяет, нужно ли отправить опросы"""
    while True:
        try:
            await _run_poll_check()
        except Exception as e:
            logger.exception("Ошибка в планировщике опросов: %s", e)
        await asyncio.sleep(60)
