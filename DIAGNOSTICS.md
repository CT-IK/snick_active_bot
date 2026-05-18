# Диагностика проблем входа

## Шаг 1: Проверка системы

```bash
docker-compose exec web python test_system.py
```

Этот скрипт проверит:
- ✅ Существует ли проектник
- ✅ Работает ли хэширование паролей
- ✅ Доступен ли API

## Шаг 2: Тест входа

```bash
docker-compose exec web python test_login.py
```

Введите логин и пароль проектника. Скрипт проверит:
- ✅ Найден ли пользователь
- ✅ Правильно ли работает проверка пароля

## Шаг 3: Проверка через API напрямую

```bash
# Проверка доступности API
curl http://localhost:8000/

# Попытка входа
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login": "PM", "password": "terminator_228!"}'
```

## Шаг 4: Проверка логов

```bash
# Просмотр логов контейнера
docker-compose logs web

# Просмотр логов в реальном времени
docker-compose logs -f web
```

## Шаг 5: Проверка пользователей в БД

```bash
docker-compose exec web python check_users.py
```

## Возможные проблемы и решения

### Проблема: "Неверный логин или пароль"

**Решение 1:** Пароль был создан со старой версией passlib
- Пересоздайте проектника с новым паролем
- Или обновите пароль существующего пользователя

**Решение 2:** Контейнер не пересобран после изменений
```bash
docker-compose down
docker-compose up --build
```

### Проблема: API недоступен

**Решение:**
```bash
# Проверьте статус контейнера
docker-compose ps

# Перезапустите контейнер
docker-compose restart

# Или пересоберите
docker-compose up --build
```

### Проблема: Пароль не работает после обновления кода

**Решение:** Пароли, созданные через passlib, не совместимы с прямым bcrypt
- Нужно пересоздать пользователя:
```bash
docker-compose exec web python create_project_manager.py
```

## Быстрая проверка через браузер

1. Откройте: http://localhost:8000
2. Откройте консоль разработчика (F12)
3. Попробуйте войти
4. Проверьте ошибки в консоли и Network tab

## Проверка через curl

```bash
# 1. Проверка API
curl http://localhost:8000/

# 2. Вход
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login": "ваш_логин", "password": "ваш_пароль"}' \
  -v

# 3. Проверка с токеном (после успешного входа)
curl http://localhost:8000/api/users/me \
  -H "Authorization: Bearer ВАШ_ТОКЕН"
```
