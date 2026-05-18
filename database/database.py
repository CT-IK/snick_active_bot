"""Настройка базы данных и сессий"""
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from database.models import Base
from config import DB_URL


engine = create_async_engine(
    DB_URL,
    echo=False, # TODO: Убрать нахуй в проде  
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Миграция: добавить колонки опроса, если их нет (SQLite)
        def _add_poll_columns(sync_conn):
            from sqlalchemy import text
            for col, defn in [
                ("poll_interval_days", "INTEGER"),
                ("poll_time", "VARCHAR(5)"),
                ("last_polled_at", "DATETIME"),
            ]:
                try:
                    sync_conn.execute(text(f"ALTER TABLE tasks ADD COLUMN {col} {defn}"))
                except Exception:
                    pass  # колонка уже есть
            try:
                sync_conn.execute(text("ALTER TABLE task_poll_responses ADD COLUMN status_at_poll VARCHAR(20)"))
            except Exception:
                pass
        await conn.run_sync(_add_poll_columns)


async def close_db():
    await engine.dispose()
