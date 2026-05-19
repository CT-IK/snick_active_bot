# Схема базы данных

Task Tracker (HSM) — SQLite, async SQLAlchemy 2.0. Таблицы создаются автоматически
из ORM-моделей ([database/models.py](../database/models.py)) при старте приложения.

## ER-диаграмма

```mermaid
erDiagram
    users {
        int id PK
        int telegram_id "unique, nullable"
        string username "nullable"
        string full_name "nullable"
        enum role "project_manager / main_organizer / responsible / worker"
        string login "unique, nullable"
        string password_hash "nullable"
        int created_by_id FK "nullable, ссылка на users (иерархия)"
        datetime created_at
        datetime updated_at
    }

    projects {
        int id PK
        string name
        datetime created_at
        datetime updated_at
    }

    workgroups {
        int id PK
        string name
        string description "nullable"
        int created_by_id FK "создатель группы"
        int responsible_id FK "nullable, ответственный"
        datetime created_at
        datetime updated_at
    }

    tasks {
        int id PK
        string title
        string description "nullable"
        enum status "new / in_progress / review / done / cancelled"
        int project_id FK "nullable"
        int workgroup_id FK "nullable"
        int created_by_id FK "автор задачи"
        int assigned_to_id FK "nullable, основной исполнитель (legacy)"
        datetime created_at
        datetime updated_at
        datetime due_date "nullable, дедлайн"
        datetime completed_at "nullable"
        int poll_interval_days "nullable, периодичность опроса"
        string poll_time "nullable, HH:MM"
        datetime last_polled_at "nullable"
        int telegram_message_id "nullable"
        int telegram_chat_id "nullable"
    }

    task_assignees {
        int task_id PK,FK
        int user_id PK,FK
    }

    workgroup_users {
        int workgroup_id PK,FK
        int user_id PK,FK
    }

    task_poll_responses {
        int id PK
        int task_id FK
        int user_id FK
        datetime polled_at
        string response_text "nullable, ответ исполнителя"
        string status_at_poll "nullable, статус задачи на момент опроса"
    }

    task_statuses {
        int id PK
        int task_id FK
        enum status
        int changed_by_id FK "nullable"
        string comment "nullable"
        datetime created_at
    }

    users ||--o{ users : "created_by (иерархия ролей)"
    users ||--o{ workgroups : "created_by"
    users ||--o{ workgroups : "responsible"
    users ||--o{ tasks : "created_by"
    users ||--o{ tasks : "assigned_to"
    projects ||--o{ tasks : "содержит"
    workgroups ||--o{ tasks : "содержит"
    tasks ||--o{ task_assignees : ""
    users ||--o{ task_assignees : ""
    workgroups ||--o{ workgroup_users : ""
    users ||--o{ workgroup_users : ""
    tasks ||--o{ task_poll_responses : ""
    users ||--o{ task_poll_responses : ""
    tasks ||--o{ task_statuses : ""
    users ||--o{ task_statuses : "changed_by"
```

## Таблицы

| Таблица | Назначение |
|---------|-----------|
| `users` | Пользователи. Иерархия подчинения — через самоссылку `created_by_id`. Роль `worker` не имеет доступа к вебу. |
| `projects` | Проекты. Контейнер верхнего уровня для задач. |
| `workgroups` | Рабочие группы. Создаются проектником / главным организатором, имеют ответственного. |
| `tasks` | Задачи. Статус, дедлайн, привязка к проекту/группе, настройки Telegram-опроса. |
| `task_poll_responses` | Ответы исполнителей на опросы-напоминания из Telegram-бота. |
| `task_statuses` | История изменений статусов задач. |
| `task_assignees` | Связующая M2M: задача ↔ исполнители. |
| `workgroup_users` | Связующая M2M: рабочая группа ↔ участники. |

## Связи

- **Иерархия пользователей** — `users.created_by_id → users.id` (самоссылка, `ON DELETE SET NULL`).
- **Исполнители задачи** — many-to-many через `task_assignees`. Поле `tasks.assigned_to_id` оставлено для обратной совместимости и хранит первого исполнителя.
- **Участники группы** — many-to-many через `workgroup_users`.
- **Задача** принадлежит опционально проекту и опциональной рабочей группе (`ON DELETE SET NULL`).

### Правила удаления (ON DELETE)

| Внешний ключ | Поведение |
|--------------|-----------|
| `users.created_by_id` | SET NULL |
| `workgroups.created_by_id` | CASCADE |
| `workgroups.responsible_id` | SET NULL |
| `tasks.project_id` / `tasks.workgroup_id` / `tasks.assigned_to_id` | SET NULL |
| `tasks.created_by_id` | CASCADE |
| `task_poll_responses.*`, `task_statuses.task_id`, обе M2M-таблицы | CASCADE |
| `task_statuses.changed_by_id` | SET NULL |

## Перечисления (enum)

- **`UserRoleEnum`**: `project_manager`, `main_organizer`, `responsible`, `worker`
- **`TaskStatusEnum`**: `new`, `in_progress`, `review`, `done`, `cancelled`

## Примечания

- Таблица **`task_statuses`** определена в моделях, но в текущем коде записи в неё
  **не создаются** — изменение статуса пишется напрямую в `tasks.status`. Таблица
  остаётся пустой (потенциальная точка для будущего аудита истории).
- Колонки опроса (`poll_interval_days`, `poll_time`, `last_polled_at`,
  `task_poll_responses.status_at_poll`) добавляются миграцией `ALTER TABLE` в
  [database/database.py](../database/database.py) для совместимости со старыми БД.
- Заметки вкладки «Шоб не забыть» в БД **не хранятся** — они живут только в
  `localStorage` браузера.
