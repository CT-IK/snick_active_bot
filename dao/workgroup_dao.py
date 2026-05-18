"""DAO для работы с рабочими группами"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import WorkGroup, Task, TaskPollResponse


def _workgroup_options(q):
    """Eager load для избежания lazy load в async (в т.ч. tasks.assignees, tasks.poll_responses для TaskResponse)"""
    return q.options(
        selectinload(WorkGroup.responsible),
        selectinload(WorkGroup.created_by),
        selectinload(WorkGroup.members),
        selectinload(WorkGroup.tasks).selectinload(Task.assignees),
        selectinload(WorkGroup.tasks).selectinload(Task.poll_responses).selectinload(TaskPollResponse.user),
    )


class WorkGroupDAO:
    """Data Access Object для рабочих групп"""
    
    @staticmethod
    async def get_by_id(session: AsyncSession, workgroup_id: int) -> Optional[WorkGroup]:
        """Получить рабочую группу по ID"""
        q = select(WorkGroup).where(WorkGroup.id == workgroup_id)
        result = await session.execute(_workgroup_options(q))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all(session: AsyncSession, skip: int = 0, limit: int = 100) -> List[WorkGroup]:
        """Получить все рабочие группы"""
        q = select(WorkGroup).offset(skip).limit(limit)
        result = await session.execute(_workgroup_options(q))
        return list(result.scalars().all())
    
    @staticmethod
    async def get_by_creator(session: AsyncSession, creator_id: int) -> List[WorkGroup]:
        """Получить рабочие группы, созданные пользователем"""
        q = select(WorkGroup).where(WorkGroup.created_by_id == creator_id)
        result = await session.execute(_workgroup_options(q))
        return list(result.scalars().all())
    
    @staticmethod
    async def get_by_responsible(session: AsyncSession, responsible_id: int) -> List[WorkGroup]:
        """Получить рабочие группы, где пользователь ответственный"""
        q = select(WorkGroup).where(WorkGroup.responsible_id == responsible_id)
        result = await session.execute(_workgroup_options(q))
        return list(result.scalars().all())
    
    @staticmethod
    async def create(session: AsyncSession, workgroup: WorkGroup) -> WorkGroup:
        """Создать рабочую группу"""
        session.add(workgroup)
        await session.flush()
        await session.refresh(workgroup)
        return workgroup
    
    @staticmethod
    async def update(session: AsyncSession, workgroup: WorkGroup) -> WorkGroup:
        """Обновить рабочую группу"""
        await session.flush()
        await session.refresh(workgroup)
        return workgroup
    
    @staticmethod
    async def delete(session: AsyncSession, workgroup_id: int) -> bool:
        """Удалить рабочую группу"""
        workgroup = await WorkGroupDAO.get_by_id(session, workgroup_id)
        if workgroup:
            await session.delete(workgroup)
            await session.flush()
            return True
        return False
