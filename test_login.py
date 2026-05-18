"""Скрипт для тестирования входа"""
import asyncio
import sys
from database import get_session
from dao.user_dao import UserDAO
from database.models import UserRoleEnum
from utils.auth import verify_password


async def test_login():
    """Тест входа пользователя"""
    print("=" * 60)
    print("ТЕСТ ВХОДА")
    print("=" * 60)
    
    login = input("\nВведите логин: ").strip()
    password = input("Введите пароль: ").strip()
    
    # Очистка от невалидных символов
    login = login.encode('utf-8', errors='ignore').decode('utf-8')
    
    try:
        async with get_session() as session:
            user = await UserDAO.get_by_login(session, login)
            
            if not user:
                print(f"\n❌ Пользователь с логином '{login}' не найден!")
                return False
            
            print(f"\n✅ Пользователь найден:")
            print(f"   ID: {user.id}")
            print(f"   Логин: {user.login}")
            print(f"   Имя: {user.full_name or 'Не указано'}")
            print(f"   Роль: {user.role.value}")
            print(f"   Пароль установлен: {'Да' if user.password_hash else 'Нет'}")
            
            if not user.password_hash:
                print("\n❌ Пароль не установлен для этого пользователя!")
                return False
            
            # Проверяем пароль
            print("\nПроверка пароля...")
            if verify_password(password, user.password_hash):
                print("✅ Пароль верный!")
                return True
            else:
                print("❌ Пароль неверный!")
                return False
                
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_login())
    sys.exit(0 if success else 1)
