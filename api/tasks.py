"""API endpoints для задач"""
from typing import List, Optional
from sqlalchemy import select
from pydantic import BaseModel
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Query
from sqlalchemy import insert, delete
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, UserRoleEnum, TaskStatusEnum, TaskPollResponse, task_assignees
from dao.task_dao import TaskDAO
from dao.workgroup_dao import WorkGroupDAO
from dao.user_dao import UserDAO
from schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskWithRelations
from schemas.user import UserResponse
from api.dependencies import get_current_user, get_db
from services.telegram_notify import notify_task_assigned, notify_task_poll

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _validate_poll_time(poll_time: Optional[str]) -> None:
    if not poll_time:
        return
    import re
    if not re.match(r"^([01]?\d|2[0-3]):([0-5]\d)$", poll_time.strip()):
        raise HTTPException(status_code=400, detail="poll_time должен быть в формате HH:MM (например 09:00)")


@router.get("/", response_model=List[TaskResponse])
async def get_tasks(
    skip: int = 0,
    limit: int = 100,
    workgroup_id: int = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить список задач"""
    if workgroup_id:
        tasks = await TaskDAO.get_by_workgroup(db, workgroup_id)
    else:
        tasks = await TaskDAO.get_all(db, skip=skip, limit=limit)
    
    return [TaskResponse.model_validate(t) for t in tasks]


@router.get("/assignable-users", response_model=List[UserResponse])
async def get_task_assignable_users(
    workgroup_id: Optional[int] = Query(None, description="ID рабочей группы — вернёт участников группы"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Пользователи, которых можно назначить исполнителями задачи.
    Если указан workgroup_id — возвращаются участники этой группы.
    Иначе — все assignable пользователи (с учётом иерархии)."""
    if workgroup_id:
        wg = await WorkGroupDAO.get_by_id(db, workgroup_id)
        if not wg:
            raise HTTPException(status_code=404, detail="Рабочая группа не найдена")
        users = list(wg.members) if wg.members else []
    else:
        if current_user.role == UserRoleEnum.PROJECT_MANAGER:
            users = await UserDAO.get_all(db, skip=0, limit=500)
        elif current_user.role == UserRoleEnum.MAIN_ORGANIZER:
            all_users = await UserDAO.get_all(db, skip=0, limit=500)
            users = [u for u in all_users if u.role != UserRoleEnum.PROJECT_MANAGER]
        elif current_user.role == UserRoleEnum.RESPONSIBLE:
            users = await UserDAO.get_created_by(db, current_user.id)
        else:
            users = []
    return [UserResponse.model_validate(u) for u in users]


@router.get("/my", response_model=List[TaskResponse])
async def get_my_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить задачи, назначенные текущему пользователю"""
    tasks = await TaskDAO.get_by_assigned_to(db, current_user.id)
    return [TaskResponse.model_validate(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskWithRelations)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить задачу по ID"""
    task = await TaskDAO.get_by_id(db, task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задача не найдена"
        )
    
    return TaskWithRelations.model_validate(task)


async def _send_task_assigned_notifications(
    assignee_telegram_ids: List[int], title: str, description: str = ""
):
    """Отправить уведомления в Telegram назначенным исполнителям (вызывается в фоне)"""
    for tid in assignee_telegram_ids:
        await notify_task_assigned(tid, title, description or "")


@router.post("/", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Создать задачу"""
    from database.models import Task
    
    # Проверка рабочей группы, если указана
    if task_data.workgroup_id:
        workgroup = await WorkGroupDAO.get_by_id(db, task_data.workgroup_id)
        if not workgroup:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Рабочая группа не найдена"
            )
    
    assignee_ids = list(task_data.assignee_ids) if task_data.assignee_ids else []
    if task_data.assigned_to_id and task_data.assigned_to_id not in assignee_ids:
        assignee_ids.insert(0, task_data.assigned_to_id)  # обратная совместимость
    
    _validate_poll_time(task_data.poll_time)
    task = Task(
        title=task_data.title,
        description=task_data.description,
        status=task_data.status,
        project_id=task_data.project_id,
        workgroup_id=task_data.workgroup_id,
        created_by_id=current_user.id,
        assigned_to_id=assignee_ids[0] if assignee_ids else None,
        due_date=task_data.due_date,
        poll_interval_days=task_data.poll_interval_days if task_data.poll_interval_days else None,
        poll_time=task_data.poll_time
    )
    
    created_task = await TaskDAO.create(db, task)
    for uid in assignee_ids:
        await db.execute(insert(task_assignees).values(task_id=created_task.id, user_id=uid))
    await db.flush()
    await db.refresh(created_task)

    # Собрать telegram_id назначенных для уведомлений (до закрытия сессии)
    notify_ids = []
    for uid in assignee_ids:
        user = await UserDAO.get_by_id(db, uid)
        if user and user.telegram_id:
            notify_ids.append(user.telegram_id)
    if notify_ids:
        background_tasks.add_task(
            _send_task_assigned_notifications,
            notify_ids, task_data.title, task_data.description
        )
    # Перезагружаем задачу со всеми связями (assignees, poll_responses), чтобы избежать MissingGreenlet при сериализации
    task_for_response = await TaskDAO.get_by_id(db, created_task.id)
    return TaskResponse.model_validate(task_for_response)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Обновить задачу"""
    task = await TaskDAO.get_by_id(db, task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задача не найдена"
        )
    
    old_assignee_ids = set(task.assignee_ids) if task.assignees else set()
    
    # Обновление полей
    if task_data.title is not None:
        task.title = task_data.title
    if task_data.description is not None:
        task.description = task_data.description
    if task_data.status is not None:
        task.status = task_data.status
        if task_data.status == TaskStatusEnum.DONE:
            from datetime import datetime
            task.completed_at = datetime.utcnow()
    if task_data.project_id is not None:
        task.project_id = task_data.project_id
    if task_data.workgroup_id is not None:
        task.workgroup_id = task_data.workgroup_id
    if task_data.assigned_to_id is not None:
        task.assigned_to_id = task_data.assigned_to_id
    if task_data.assignee_ids is not None:
        await db.execute(delete(task_assignees).where(task_assignees.c.task_id == task_id))
        for uid in task_data.assignee_ids:
            await db.execute(insert(task_assignees).values(task_id=task_id, user_id=uid))
        task.assigned_to_id = task_data.assignee_ids[0] if task_data.assignee_ids else None
        await db.flush()

        # Уведомить только вновь добавленных исполнителей
        new_assignee_ids = set(task_data.assignee_ids)
        newly_added = new_assignee_ids - old_assignee_ids
        notify_ids = []
        for uid in newly_added:
            user = await UserDAO.get_by_id(db, uid)
            if user and user.telegram_id:
                notify_ids.append(user.telegram_id)
        if notify_ids:
            title = task_data.title or task.title
            desc = task_data.description if task_data.description is not None else task.description
            background_tasks.add_task(
                _send_task_assigned_notifications,
                notify_ids, title, desc or ""
            )

    if task_data.due_date is not None:
        task.due_date = task_data.due_date
    if task_data.poll_interval_days is not None:
        task.poll_interval_days = task_data.poll_interval_days if task_data.poll_interval_days else None
    if task_data.poll_time is not None:
        _validate_poll_time(task_data.poll_time)
        task.poll_time = task_data.poll_time

    updated_task = await TaskDAO.update(db, task)
    if task_data.assignee_ids is not None:
        await db.refresh(updated_task)
    return TaskResponse.model_validate(updated_task)


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Удалить задачу"""
    task = await TaskDAO.get_by_id(db, task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задача не найдена"
        )
    
    # Только создатель или проектник может удалять
    if task.created_by_id != current_user.id and current_user.role != UserRoleEnum.PROJECT_MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для удаления задачи"
        )
    
    await TaskDAO.delete(db, task_id)
    return {"message": "Задача удалена"}


class PollResponseSubmit(BaseModel):
    """Тело запроса для сохранения ответа на опрос"""
    user_id: int
    response_text: str


@router.post("/{task_id}/poll-response")
async def submit_poll_response(
    task_id: int,
    body: PollResponseSubmit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Сохранить ответ пользователя на опрос о задаче (вызывается ботом или при обновлении статуса)"""
    result = await db.execute(
        select(TaskPollResponse)
        .where(
            TaskPollResponse.task_id == task_id,
            TaskPollResponse.user_id == body.user_id,
            TaskPollResponse.response_text.is_(None),
        )
        .order_by(TaskPollResponse.polled_at.desc())
        .limit(1)
    )
    poll_rec = result.scalar_one_or_none()
    if poll_rec:
        poll_rec.response_text = (body.response_text or "").strip() or None
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
        return {"ok": True}
    return {"ok": False, "message": "Нет ожидающего ответа опроса"}


@router.post("/{task_id}/nudge")
async def nudge_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Принудительно отправить напоминание-опрос исполнителям задачи в Telegram (тык)"""
    from datetime import datetime
    task = await TaskDAO.get_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    if not task.assignees:
        return {"ok": False, "message": "Нет исполнителей у задачи"}
    now = datetime.utcnow()
    sent = 0
    for user in task.assignees:
        if user.telegram_id:
            try:
                await notify_task_poll(user.telegram_id, task.title, task.id)
                db.add(TaskPollResponse(
                    task_id=task.id,
                    user_id=user.id,
                    polled_at=now,
                    response_text=None,
                    status_at_poll=task.status.value if task.status else None,
                ))
                sent += 1
            except Exception:
                pass
    task.last_polled_at = now
    await db.commit()
    return {"ok": True, "sent": sent, "message": f"Напоминание отправлено {sent} чел." if sent else "Нет исполнителей с Telegram"}
