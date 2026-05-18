"""Главный файл FastAPI приложения"""
import logging
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import uvicorn

from api import auth, users, tasks, workgroups
from database import init_db

app = FastAPI(
    title="Task Tracker API",
    description="API для управления задачами",
    version="1.0.0"
)

# CORS настройки: с credentials браузер не отправляет Authorization при allow_origins=["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://192.168.65.1:8000",
        "http://0.0.0.0:8000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tasks.router)
app.include_router(workgroups.router)


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    import asyncio
    from services.task_poll_scheduler import poll_scheduler_loop
    from services.telegram_bot_poller import bot_updates_loop
    await init_db()
    asyncio.create_task(poll_scheduler_loop())
    asyncio.create_task(bot_updates_loop())


# Статические файлы для фронтенда
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    @app.get("/")
    async def serve_app():
        """Отдача главной страницы приложения"""
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "Task Tracker API", "version": "1.0.0"}
else:
    @app.get("/")
    async def root():
        """Корневой endpoint"""
        return {"message": "Task Tracker API", "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
