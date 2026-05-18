# Task Tracker - Система управления задачами

Веб-приложение для управления задачами с иерархией ролей и Telegram ботом.

## Структура проекта

- `database/` - Модели БД и настройка
- `api/` - API endpoints (FastAPI)
- `dao/` - Data Access Object слой
- `schemas/` - Pydantic схемы
- `services/` - Бизнес-логика
- `utils/` - Утилиты
- `static/` - Фронтенд (HTML/CSS/JS)
- `main.py` - Главный файл приложения

## Быстрый старт с Docker

### Вариант 1: Использование скрипта (рекомендуется)

```bash
./start.sh
```

### Вариант 2: Ручной запуск

```bash
# Сборка и запуск
docker-compose up --build

# В фоновом режиме
docker-compose up -d --build

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

Приложение будет доступно по адресу: **http://localhost:8000**

### Создание проектника

После первого запуска нужно создать проектника (первого пользователя):

```bash
docker-compose exec web python create_project_manager.py
```

Или интерактивно:

```bash
docker-compose exec web bash
python create_project_manager.py
```

### Полезные команды

```bash
# Перезапуск контейнера
docker-compose restart

# Просмотр статуса
docker-compose ps

# Очистка (удаление контейнеров и volumes)
docker-compose down -v
```

## Локальный запуск (без Docker)

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Инициализация БД

```bash
python init_db.py
```

### 3. Создание проектника

```bash
python create_project_manager.py
```

### 4. Запуск сервера

```bash
python main.py
```

Приложение будет доступно по адресу: http://localhost:8000

## Иерархия ролей

1. **PROJECT_MANAGER** (Проектник) - полный доступ
2. **MAIN_ORGANIZER** (Главный организатор) - может создавать группы и добавлять ответственных
3. **RESPONSIBLE** (Ответственный) - может создавать подчиненных и управлять задачами
4. **WORKER** (Работник) - только через Telegram бота

## API Endpoints

- `POST /api/auth/login` - Вход в систему
- `GET /api/users/me` - Информация о текущем пользователе
- `GET /api/users/` - Список пользователей
- `POST /api/users/` - Создать пользователя
- `GET /api/tasks/` - Список задач
- `POST /api/tasks/` - Создать задачу
- `GET /api/workgroups/` - Список рабочих групп
- `POST /api/workgroups/` - Создать рабочую группу

## Переменные окружения

Создайте файл `.env`:

```env
JWT_SECRET_KEY=your-secret-key-here
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
```

## Структура БД

- SQLite3 с async ORM (SQLAlchemy 2.0)
- Модели: User, Task, Project, WorkGroup, TaskStatus
- Иерархия пользователей через `created_by_id`
