"""FSM-состояния бота."""
from aiogram.fsm.state import State, StatesGroup


class PollResponseState(StatesGroup):
    """Ожидание произвольного текстового ответа на опрос о задаче."""

    waiting_for_text = State()
