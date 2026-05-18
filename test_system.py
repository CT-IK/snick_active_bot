"""Скрипт для проверки системы"""
import asyncio
import sys
from database import get_session
from dao.user_dao import UserDAO
from database.models import UserRoleEnum
from utils.auth import verify_password, get_password_hash


async def check_system():
    """Проверка системы"""
    print("=" * 60)
    print("ПРОВЕРКА СИСТЕМЫ")
    print("=" * 60)
    
    # 1. Проверка БД
    print("\n1. Проверка базы данных...")
    try:
        async with get_session() as session:
            # Проверяем проектника
            project_managers = await UserDAO.get_by_role(session, UserRoleEnum.PROJECT_MANAGER)
            if project_managers:
                print("   ✅ Проектник найден:")
                for pm in project_managers:
                    print(f"      - ID: {pm.id}")
                    print(f"      - Логин: {pm.login}")
                    print(f"      - Имя: {pm.full_name or 'Не указано'}")
                    print(f"      - Пароль установлен: {'Да' if pm.password_hash else 'Нет'}")
            else:
                print("   ❌ Проектник НЕ найден!")
                print("   Запустите: python create_project_manager.py")
                return False
            
            # Проверяем других пользователей
            all_users = await UserDAO.get_all(session)
            print(f"\n   Всего пользователей: {len(all_users)}")
            
    except Exception as e:
        print(f"   ❌ Ошибка подключения к БД: {e}")
        return False
    
    # 2. Проверка хэширования паролей
    print("\n2. Проверка хэширования паролей...")
    try:
        test_password = "test123"
        hashed = get_password_hash(test_password)
        verified = verify_password(test_password, hashed)
        if verified:
            print("   ✅ Хэширование паролей работает корректно")
        else:
            print("   ❌ Ошибка проверки пароля!")
            return False
    except Exception as e:
        print(f"   ❌ Ошибка хэширования: {e}")
        return False
    
    # 3. Проверка API (если запущен)
    print("\n3. Проверка API...")
    try:
        import urllib.request
        import json
        
        # Проверяем доступность API
        try:
            response = urllib.request.urlopen('http://localhost:8000/', timeout=2)
            if response.status == 200:
                print("   ✅ API доступен на http://localhost:8000")
            else:
                print(f"   ⚠️  API отвечает со статусом: {response.status}")
        except urllib.error.URLError:
            print("   ⚠️  API недоступен (возможно, не запущен)")
            print("   Запустите: docker-compose up")
    except Exception as e:
        print(f"   ⚠️  Не удалось проверить API: {e}")
    
    print("\n" + "=" * 60)
    print("РЕКОМЕНДАЦИИ:")
    print("=" * 60)
    print("1. Убедитесь, что контейнер запущен: docker-compose ps")
    print("2. Проверьте логи: docker-compose logs web")
    print("3. Откройте в браузере: http://localhost:8000")
    print("4. Попробуйте войти с логином проектника")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    success = asyncio.run(check_system())
    sys.exit(0 if success else 1)
