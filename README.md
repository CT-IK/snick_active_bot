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

## Документация для разработчиков

Подробная документация — в каталоге [docs/](docs/):

- [docs/architecture.md](docs/architecture.md) — архитектура, слои, путь запроса, роли
- [docs/api.md](docs/api.md) — справочник REST API
- [docs/database.md](docs/database.md) — схема базы данных
- [docs/bot.md](docs/bot.md) — Telegram-бот на aiogram
- [docs/frontend.md](docs/frontend.md) — фронтенд

## Запуск через Docker

Конфигурация Docker Compose разделена на три файла:

| Файл | Назначение |
|------|-----------|
| `docker-compose.yml` | базовая часть, общая для всех окружений |
| `docker-compose.override.yml` | локальная разработка (подхватывается автоматически) |
| `docker-compose.prod.yml` | продакшен |

### Локальная разработка

```bash
docker compose up --build
```

`docker-compose.override.yml` подхватывается автоматически — включены
hot-reload и монтирование исходников (правки кода применяются без пересборки).
Приложение доступно на **http://localhost:8004**

```bash
docker compose up -d --build     # запуск в фоне
docker compose logs -f           # логи
docker compose down              # остановка
```

### Продакшен

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Перед запуском задайте переменные окружения — в файле `.env` рядом с
compose-файлами или в окружении shell:

```env
JWT_SECRET_KEY=длинная-случайная-строка    # обязательно
TELEGRAM_BOT_TOKEN=токен-telegram-бота      # опционально
APP_PORT=8000                               # порт на хосте (по умолчанию 8000)
```

### Создание проектника

После первого запуска создайте проектника (первого пользователя):

```bash
docker compose exec web python create_project_manager.py
```

### Полезные команды

```bash
docker compose ps          # статус контейнера
docker compose restart     # перезапуск
docker compose down -v     # остановка с удалением volumes
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
# snick_active_bot
# snick_active_bot
# snick_active_bot
