from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import get_all_user_tg_ids
from keyboards.inline_admin import get_broadcast_confirm_kb
from states.admin_states import BroadcastState
from services.broadcast_service import BroadcastService
from utils.ui_cleaner import send_or_edit_screen, delete_user_message
from utils.formatters import DIVIDER

router = Router(name="admin_broadcast")


@router.callback_query(F.data == "adm_broadcast")
async def start_broadcast(call: CallbackQuery, state: FSMContext):
    """Начало создания рассылки."""
    await state.set_state(BroadcastState.waiting_for_content)
    text = (
        f"📢 <b>Конструктор рассылки</b>\n"
        f"{DIVIDER}\n"
        f"Отправьте текст сообщения или фото с подписью, которое увидят все клиенты бота:\n\n"
        f"<i>Поддерживается HTML-разметка (жирный, курсив, ссылки).</i>"
    )
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В админку", callback_data="adm_main")]
    ])
    await send_or_edit_screen(call, text, reply_markup=cancel_kb, state=state)
    await call.answer()


@router.message(BroadcastState.waiting_for_content)
async def process_broadcast_content(message: Message, state: FSMContext, bot: Bot):
    """Предпросмотр сообщения с удалением входящего текста."""
    photo_id = message.photo[-1].file_id if message.photo else None
    content_text = message.caption or message.text or ""
    await delete_user_message(message)

    if not content_text and not photo_id:
        text = "⚠️ Сообщение не может быть пустым. Отправьте текст или фото:"
        await send_or_edit_screen(message, text, state=state, bot=bot)
        return

    await state.update_data(text=content_text, photo_id=photo_id)
    await state.set_state(BroadcastState.waiting_for_confirmation)

    preview_text = (
        f"👀 <b>Предпросмотр рассылки:</b>\n"
        f"{DIVIDER}\n"
        f"{content_text}"
    )

    await send_or_edit_screen(
        message,
        preview_text,
        photo_id=photo_id,
        reply_markup=get_broadcast_confirm_kb(),
        state=state,
        bot=bot
    )


@router.callback_query(BroadcastState.waiting_for_confirmation, F.data == "adm_start_broadcast")
async def confirm_broadcast(call: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    """Запуск процесса рассылки."""
    data = await state.get_data()
    text = data.get("text", "")
    photo_id = data.get("photo_id")

    user_ids = await get_all_user_tg_ids(session)
    await state.clear()

    loading_text = (
        f"⏳ <b>Рассылка запущена...</b>\n"
        f"{DIVIDER}\n"
        f"Получателей в очереди: <b>{len(user_ids)}</b>\n"
        f"Ожидайте формирования отчета."
    )
    await send_or_edit_screen(call, loading_text, state=state)

    broadcast_service = BroadcastService(bot)
    stats = await broadcast_service.run_broadcast(user_ids, text, photo_id)

    report_text = (
        f"📢 <b>Рассылка успешно выполнена!</b>\n"
        f"{DIVIDER}\n"
        f"👥 Всего адресатов: <b>{stats['total']}</b>\n"
        f"✅ Успешно доставлено: <b>{stats['success']}</b>\n"
        f"⛔️ Заблокировали бота: <b>{stats['blocked']}</b>\n"
        f"⚠️ Ошибок: <b>{stats['errors']}</b>"
    )

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В админку", callback_data="adm_main")]
    ])
    await send_or_edit_screen(call, report_text, reply_markup=back_kb, state=state)
    await call.answer()


@router.callback_query(BroadcastState.waiting_for_confirmation, F.data == "adm_cancel_broadcast")
async def cancel_broadcast(call: CallbackQuery, state: FSMContext):
    """Отмена рассылки."""
    await state.clear()
    text = "❌ Рассылка отменена."
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В админку", callback_data="adm_main")]
    ])
    await send_or_edit_screen(call, text, reply_markup=back_kb, state=state)
    await call.answer()
