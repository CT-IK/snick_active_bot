"""DAO для работы с проектами"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Project


class ProjectDAO:
    """Data Access Object для проектов"""
    
    @staticmethod
    async def get_by_id(session: AsyncSession, project_id: int) -> Optional[Project]:
        """Получить проект по ID"""
        result = await session.execute(select(Project).where(Project.id == project_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all(session: AsyncSession, skip: int = 0, limit: int = 100) -> List[Project]:
        """Получить все проекты"""
        result = await session.execute(select(Project).offset(skip).limit(limit))
        return list(result.scalars().all())
    
    @staticmethod
    async def create(session: AsyncSession, project: Project) -> Project:
        """Создать проект"""
        session.add(project)
        await session.flush()
        await session.refresh(project)
        return project
    
    @staticmethod
    async def update(session: AsyncSession, project: Project) -> Project:
        """Обновить проект"""
        await session.flush()
        await session.refresh(project)
        return project
    
    @staticmethod
    async def delete(session: AsyncSession, project_id: int) -> bool:
        """Удалить проект"""
        project = await ProjectDAO.get_by_id(session, project_id)
        if project:
            await session.delete(project)
            await session.flush()
            return True
        return False
