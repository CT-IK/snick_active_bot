"""Скрипт для создания проектника"""
import asyncio
from database import get_session
from database.models import User, UserRoleEnum
from dao.user_dao import UserDAO
from utils.auth import get_password_hash


async def create_project_manager():
    """Создать проектника"""
    async with get_session() as session:
        # Проверяем, есть ли уже проектник
        existing = await UserDAO.get_by_role(session, UserRoleEnum.PROJECT_MANAGER)
        if existing:
            print("Проектник уже существует!")
            return
        
        # Создаем проектника
        login = input("Введите логин для проектника: ")
        password = input("Введите пароль для проектника: ")
        full_name = input("Введите полное имя (опционально): ") or None
        
        project_manager = User(
            login=login,
            password_hash=get_password_hash(password),
            full_name=full_name,
            role=UserRoleEnum.PROJECT_MANAGER,
        )
        
        created = await UserDAO.create(session, project_manager)
        print(f"Проектник успешно создан! ID: {created.id}, Логин: {created.login}")


if __name__ == "__main__":
    asyncio.run(create_project_manager())
