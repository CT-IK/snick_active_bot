"""Скрипт для просмотра всех пользователей с логинами"""
import asyncio
from database import get_session
from dao.user_dao import UserDAO


async def list_users():
    """Показать всех пользователей"""
    print("=" * 60)
    print("СПИСОК ПОЛЬЗОВАТЕЛЕЙ")
    print("=" * 60)
    
    try:
        async with get_session() as session:
            users = await UserDAO.get_all(session)
            
            if not users:
                print("\n❌ Пользователи не найдены!")
                return
            
            print(f"\nВсего пользователей: {len(users)}\n")
            
            for user in users:
                print(f"ID: {user.id}")
                print(f"  Логин: {repr(user.login)}")  # repr покажет точное значение
                print(f"  Имя: {user.full_name or 'Не указано'}")
                print(f"  Роль: {user.role.value}")
                print(f"  Пароль установлен: {'Да' if user.password_hash else 'Нет'}")
                if user.password_hash:
                    print(f"  Хэш пароля (первые 20 символов): {user.password_hash[:20]}...")
                print("-" * 60)
                
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(list_users())
