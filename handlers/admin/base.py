from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards.inline_admin import get_admin_main_kb
from keyboards.inline_client import get_bottom_reply_kb
from utils.ui_cleaner import send_or_edit_screen, delete_user_message
from utils.formatters import format_admin_dashboard

router = Router(name="admin_base")


@router.message(Command("admin", "panel"))
async def cmd_admin_panel(message: Message, state: FSMContext):
    """Вход в панель администратора: удаляет введенную команду и выводит чистый экран."""
    await delete_user_message(message)
    await state.clear()
    text = format_admin_dashboard()
    await message.answer(
        "🛠️ Админ-панель доступна кнопкой /admin ниже.",
        reply_markup=get_bottom_reply_kb(is_admin=True)
    )
    await send_or_edit_screen(message, text, reply_markup=get_admin_main_kb(), state=state)


@router.callback_query(F.data == "adm_main")
async def cb_admin_main(call: CallbackQuery, state: FSMContext):
    """Возврат в главное меню панели администратора в том же окне."""
    await state.clear()
    text = format_admin_dashboard()
    await send_or_edit_screen(call, text, reply_markup=get_admin_main_kb(), state=state)
    await call.answer()
