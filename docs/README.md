# Документация Task Tracker

Документация для разработчиков. Впервые в проекте — начните с
[architecture.md](architecture.md).

## Содержание

| Документ | О чём |
|----------|-------|
| [architecture.md](architecture.md) | Архитектура, структура каталогов, путь запроса, роли, фоновые сервисы |
| [api.md](api.md) | Справочник REST API: все endpoints, методы, права доступа |
| [database.md](database.md) | Схема БД, таблицы, связи, ER-диаграмма |
| [bot.md](bot.md) | Telegram-бот на aiogram: структура пакета, опросы, как добавлять хендлеры |
| [frontend.md](frontend.md) | Фронтенд: SPA на чистом JS, вкладки, рендеринг, авторизация |

## Что за проект

Task Tracker (HSM) — веб-приложение для управления задачами с иерархией
ролей и Telegram-ботом.

Стек: **FastAPI + async SQLAlchemy 2.0 + SQLite**, фронтенд — vanilla JS
без сборки, бот — **aiogram 3.x**.

Установка и запуск (Docker, локально) описаны в корневом
[../README.md](../README.md).
