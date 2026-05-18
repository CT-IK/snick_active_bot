"""Скрипт для проверки существующих пользователей"""
import asyncio
from database import get_session
from dao.user_dao import UserDAO
from database.models import UserRoleEnum


async def check_users():
    """Проверить существующих пользователей"""
    async with get_session() as session:
        # Проверяем проектника
        project_managers = await UserDAO.get_by_role(session, UserRoleEnum.PROJECT_MANAGER)
        if project_managers:
            print("=" * 50)
            print("Проектник найден:")
            for pm in project_managers:
                print(f"  ID: {pm.id}")
                print(f"  Логин: {pm.login}")
                print(f"  Полное имя: {pm.full_name or 'Не указано'}")
                print(f"  Создан: {pm.created_at}")
                print("-" * 50)
        else:
            print("Проектник не найден. Запустите: python create_project_manager.py")
        
        # Проверяем главных организаторов
        main_organizers = await UserDAO.get_by_role(session, UserRoleEnum.MAIN_ORGANIZER)
        if main_organizers:
            print(f"\nГлавных организаторов: {len(main_organizers)}")
        
        # Проверяем ответственных
        responsibles = await UserDAO.get_by_role(session, UserRoleEnum.RESPONSIBLE)
        if responsibles:
            print(f"Ответственных: {len(responsibles)}")
        
        # Проверяем работников
        workers = await UserDAO.get_by_role(session, UserRoleEnum.WORKER)
        if workers:
            print(f"Работников: {len(workers)}")


if __name__ == "__main__":
    asyncio.run(check_users())
