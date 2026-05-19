"""Роутеры бота.

Чтобы добавить новый функционал — создайте модуль с собственным Router
и добавьте его в get_routers(). Порядок важен: апдейт обрабатывает первый
подходящий хендлер.
"""
from aiogram import Router

from services.bot.handlers import commands, poll


def get_routers() -> list[Router]:
    """Список роутеров в порядке подключения к Dispatcher."""
    return [commands.router, poll.router]
