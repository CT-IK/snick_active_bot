"""DAO для работы с пользователями"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, UserRoleEnum
from database import get_session


class UserDAO:
    f"""Data Access Object для пользователей"""
    
    @staticmethod
    async def get_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
        f"""Получить пользователя по ID"""
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_login(session: AsyncSession, login: str) -> Optional[User]:
        f"""Получить пользователя по логину"""
        result = await session.execute(select(User).where(User.login == login))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
        f"""Получить пользователя по Telegram ID"""
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all(session: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
        f"""Получить всех пользователей"""
        result = await session.execute(select(User).offset(skip).limit(limit))
        return list(result.scalars().all())
    
    @staticmethod
    async def get_by_role(session: AsyncSession, role: UserRoleEnum) -> List[User]:
        f"""Получить пользователей по роли"""
        result = await session.execute(select(User).where(User.role == role))
        return list(result.scalars().all())
    
    @staticmethod
    async def get_created_by(session: AsyncSession, creator_id: int) -> List[User]:
        f"""Получить пользователей, созданных указанным пользователем"""
        result = await session.execute(select(User).where(User.created_by_id == creator_id))
        return list(result.scalars().all())
    
    @staticmethod
    async def create(session: AsyncSession, user: User) -> User:
        f"""Создать пользователя"""
        session.add(user)
        await session.flush()
        await session.refresh(user)
        return user
    
    @staticmethod
    async def update(session: AsyncSession, user: User) -> User:
        f"""Обновить пользователя"""
        await session.flush()
        await session.refresh(user)
        return user
    
    @staticmethod
    async def delete(session: AsyncSession, user_id: int) -> bool:
        f"""Удалить пользователя"""
        user = await UserDAO.get_by_id(session, user_id)
        if user:
            await session.delete(user)
            await session.flush()
            return True
        return False
