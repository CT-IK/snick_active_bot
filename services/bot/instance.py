"""Singleton-объекты aiogram: Bot и Dispatcher.

Bot создаётся лениво и только при наличии токена — если TELEGRAM_BOT_TOKEN
не задан, get_bot() возвращает None, и все обращения к боту тихо пропускаются.
"""
import logging
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)

_bot: Optional[Bot] = None
_dispatcher: Optional[Dispatcher] = None


def get_bot() -> Optional[Bot]:
    """Вернуть singleton Bot или None, если токен не задан."""
    global _bot
    if _bot is None and TELEGRAM_BOT_TOKEN:
        _bot = Bot(
            token=TELEGRAM_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
    return _bot


def get_dispatcher() -> Dispatcher:
    """Вернуть singleton Dispatcher с подключёнными роутерами."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = Dispatcher(storage=MemoryStorage())
        # Импорт роутеров здесь, чтобы избежать циклических импортов
        from services.bot.handlers import get_routers

        for router in get_routers():
            _dispatcher.include_router(router)
    return _dispatcher
