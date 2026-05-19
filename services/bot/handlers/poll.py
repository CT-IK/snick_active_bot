"""Обработка опросов о задачах: inline-кнопки и текстовые ответы."""
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from services.bot.callbacks import PollAnswer, PollChoice
from services.bot.keyboards import POLL_CUSTOM, poll_choice_keyboard
from services.bot.poll_service import save_poll_response
from services.bot.states import PollResponseState

logger = logging.getLogger(__name__)
router = Router(name="poll")

_SAVED_MSG = "✅ Ответ сохранён. Администратор увидит его в таймлайне задачи."


@router.callback_query(PollAnswer.filter())
async def on_poll_answer(query: CallbackQuery, callback_data: PollAnswer, bot: Bot) -> None:
    """Нажата кнопка «Ответить» — показать варианты ответа."""
    await query.answer()
    await bot.send_message(
        query.from_user.id,
        "Как продвигается задача? Выберите вариант или напишите свой:",
        reply_markup=poll_choice_keyboard(callback_data.task_id),
    )


@router.callback_query(PollChoice.filter())
async def on_poll_choice(
    query: CallbackQuery,
    callback_data: PollChoice,
    state: FSMContext,
    bot: Bot,
) -> None:
    """Выбран вариант ответа на опрос (готовый или «напишу текст»)."""
    task_id = callback_data.task_id

    if callback_data.value == POLL_CUSTOM:
        await state.set_state(PollResponseState.waiting_for_text)
        await state.update_data(task_id=task_id)
        await query.answer()
        await bot.send_message(query.from_user.id, "Напишите ваш ответ одним сообщением:")
        return

    ok = await save_poll_response(query.from_user.id, task_id, callback_data.value)
    await query.answer("Спасибо, ответ сохранён!" if ok else "Ответ уже был сохранён")
    if ok:
        await bot.send_message(query.from_user.id, _SAVED_MSG)


@router.message(PollResponseState.waiting_for_text, F.text)
async def on_poll_custom_text(message: Message, state: FSMContext) -> None:
    """Получен произвольный текстовый ответ на опрос."""
    data = await state.get_data()
    task_id = data.get("task_id")
    await state.clear()

    text = (message.text or "").strip()
    if not text:
        await message.answer("Пустой ответ не сохранён.")
        return
    if task_id is None:
        await message.answer("Не удалось определить задачу. Нажмите «Ответить» ещё раз.")
        return

    ok = await save_poll_response(message.from_user.id, task_id, text)
    if ok:
        await message.answer(_SAVED_MSG)
    else:
        await message.answer("Не удалось сохранить (возможно, ответ уже был отправлен).")
