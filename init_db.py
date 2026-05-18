"""Скрипт для инициализации базы данных"""
import asyncio
from database import init_db, close_db


async def main():
    """Создание всех таблиц в БД"""
    print("Инициализация базы данных...")
    await init_db()
    print("База данных успешно инициализирована!")
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
