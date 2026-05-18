"""DAO для работы с задачами"""
from typing import Optional, List
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Task, TaskStatusEnum, TaskPollResponse, task_assignees


def _task_options(q):
    return q.options(
        selectinload(Task.assignees),
        selectinload(Task.poll_responses).selectinload(TaskPollResponse.user),
    )


class TaskDAO:
    """Data Access Object для задач"""
    
    @staticmethod
    async def get_by_id(session: AsyncSession, task_id: int) -> Optional[Task]:
        """Получить задачу по ID"""
        result = await session.execute(
            _task_options(select(Task).where(Task.id == task_id))
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all(session: AsyncSession, skip: int = 0, limit: int = 100) -> List[Task]:
        """Получить все задачи"""
        result = await session.execute(
            _task_options(select(Task).offset(skip).limit(limit))
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_by_workgroup(session: AsyncSession, workgroup_id: int) -> List[Task]:
        """Получить задачи рабочей группы"""
        result = await session.execute(
            _task_options(select(Task).where(Task.workgroup_id == workgroup_id))
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_by_assigned_to(session: AsyncSession, user_id: int) -> List[Task]:
        """Получить задачи, назначенные пользователю (assigned_to или в assignees)"""
        subq = select(task_assignees.c.task_id).where(task_assignees.c.user_id == user_id)
        result = await session.execute(
            _task_options(
                select(Task).where(
                    or_(Task.assigned_to_id == user_id, Task.id.in_(subq))
                )
            )
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_by_status(session: AsyncSession, status: TaskStatusEnum) -> List[Task]:
        """Получить задачи по статусу"""
        result = await session.execute(select(Task).where(Task.status == status))
        return list(result.scalars().all())
    
    @staticmethod
    async def create(session: AsyncSession, task: Task) -> Task:
        """Создать задачу"""
        session.add(task)
        await session.flush()
        await session.refresh(task)
        return task
    
    @staticmethod
    async def update(session: AsyncSession, task: Task) -> Task:
        """Обновить задачу"""
        await session.flush()
        await session.refresh(task)
        return task
    
    @staticmethod
    async def delete(session: AsyncSession, task_id: int) -> bool:
        """Удалить задачу"""
        task = await TaskDAO.get_by_id(session, task_id)
        if task:
            await session.delete(task)
            await session.flush()
            return True
        return False
