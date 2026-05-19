"""Команды бота: /start, /myid, /help."""
import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from database.database import AsyncSessionLocal
from dao.user_dao import UserDAO

logger = logging.getLogger(__name__)
router = Router(name="commands")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Приветствие. Показывает Telegram ID — он нужен админу для добавления пользователя."""
    tg_id = message.from_user.id if message.from_user else None

    db_user = None
    if tg_id is not None:
        async with AsyncSessionLocal() as db:
            db_user = await UserDAO.get_by_telegram_id(db, tg_id)

    lines = ["👋 <b>Task Tracker</b>\n"]
    if db_user:
        name = db_user.full_name or db_user.login or "пользователь"
        lines.append(f"Вы зарегистрированы как <b>{name}</b>.")
        lines.append("Здесь вы получаете назначенные задачи и напоминания по ним.")
    else:
        lines.append("Вы пока не добавлены в систему.")
        lines.append(f"Передайте администратору ваш Telegram ID: <code>{tg_id}</code>")
    lines.append("\n/myid — показать ваш ID · /help — справка")
    await message.answer("\n".join(lines))


@router.message(Command("myid"))
async def cmd_myid(message: Message) -> None:
    """Показать Telegram ID пользователя."""
    tg_id = message.from_user.id if message.from_user else "неизвестен"
    await message.answer(f"Ваш Telegram ID: <code>{tg_id}</code>")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Краткая справка по боту."""
    await message.answer(
        "ℹ️ <b>Справка</b>\n\n"
        "Бот присылает назначенные вам задачи и напоминания о ходе работы.\n"
        "На напоминание ответьте кнопкой «📝 Ответить» под сообщением.\n\n"
        "/start — начало работы\n"
        "/myid — ваш Telegram ID\n"
        "/help — эта справка"
    )
