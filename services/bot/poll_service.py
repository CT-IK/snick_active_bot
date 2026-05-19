"""Бизнес-логика опросов: сохранение ответа исполнителя в БД."""
import logging

from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import TaskPollResponse, TaskStatusEnum
from dao.task_dao import TaskDAO
from dao.user_dao import UserDAO

logger = logging.getLogger(__name__)

# Продвижение статуса задачи на следующий этап при ответе на опрос
_NEXT_STATUS = {
    TaskStatusEnum.NEW: TaskStatusEnum.IN_PROGRESS,
    TaskStatusEnum.IN_PROGRESS: TaskStatusEnum.REVIEW,
    TaskStatusEnum.REVIEW: TaskStatusEnum.DONE,
}


async def save_poll_response(telegram_id: int, task_id: int, response_text: str) -> bool:
    """Сохранить ответ пользователя на опрос о задаче.

    Находит последний неотвеченный опрос (response_text IS NULL) по паре
    задача+пользователь, записывает текст и продвигает статус задачи вперёд.
    Возвращает True, если ответ сохранён.
    """
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
        poll_rec = result.scalar_one_or_none()
        if poll_rec is None:
            return False

        poll_rec.response_text = (response_text or "").strip() or None

        task = await TaskDAO.get_by_id(db, task_id)
        if task and task.status not in (TaskStatusEnum.DONE, TaskStatusEnum.CANCELLED):
            next_status = _NEXT_STATUS.get(task.status)
            if next_status:
                task.status = next_status

        await db.commit()
        return True
