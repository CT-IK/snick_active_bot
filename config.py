"""Конфигурация приложения"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# База данных
DB_PATH = Path(__file__).parent / "database" / "tasks.db"
DB_URL = f"sqlite+aiosqlite:///{DB_PATH}"

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# JWT Settings
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 часа

# Создаем директорию для БД если её нет
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
