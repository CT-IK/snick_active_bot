"""Запуск и остановка Telegram-бота (long polling).

Бот работает фоновой задачей внутри процесса FastAPI-приложения.
"""
import asyncio
import logging
from typing import Optional

from services.bot.instance import get_bot, get_dispatcher

logger = logging.getLogger(__name__)

_polling_task: Optional[asyncio.Task] = None


async def _polling() -> None:
    """Тело фоновой задачи: запустить long polling."""
    bot = get_bot()
    dp = get_dispatcher()
    try:
        # Сбросить webhook и накопившиеся апдейты перед polling
        await bot.delete_webhook(drop_pending_updates=True)
        # handle_signals=False — обработкой сигналов управляет uvicorn
        await dp.start_polling(bot, handle_signals=False)
    except asyncio.CancelledError:
        raise
    except Exception as e:  # noqa: BLE001 — фоновая задача не должна падать молча
        logger.exception("Сбой polling Telegram-бота: %s", e)


async def start_bot() -> None:
    """Запустить бота в фоне. Безопасно вызывать, если токен не задан."""
    global _polling_task
    if get_bot() is None:
        logger.info("TELEGRAM_BOT_TOKEN не задан — Telegram-бот не запущен")
        return
    if _polling_task is not None and not _polling_task.done():
        return
    _polling_task = asyncio.create_task(_polling())
    logger.info("Telegram-бот запущен (long polling)")


async def stop_bot() -> None:
    """Остановить polling и закрыть сессию бота."""
    global _polling_task
    bot = get_bot()
    if bot is None:
        return
    if _polling_task is not None and not _polling_task.done():
        _polling_task.cancel()
        try:
            await _polling_task
        except asyncio.CancelledError:
            pass
        except Exception as e:  # noqa: BLE001
            logger.warning("Ошибка при остановке бота: %s", e)
    _polling_task = None
    try:
        await bot.session.close()
    except Exception:  # noqa: BLE001
        pass
    logger.info("Telegram-бот остановлен")
