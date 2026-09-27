from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from database.crud import set_user_ban_status
from keyboards.inline_admin import get_admin_main_kb
from keyboards.inline_client import get_bottom_reply_kb
from utils.ui_cleaner import send_or_edit_screen, delete_user_message
from utils.formatters import format_admin_dashboard

router = Router(name="admin_base")


@router.message(Command("unban"))
async def cmd_unban_user(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    bot: Bot,
) -> None:
    """Разблокировать пользователя в боте и админской группе по Telegram ID."""
    raw_user_id = (command.args or "").strip()
    if not raw_user_id.isdigit():
        await message.answer("Использование: <code>/unban Telegram_ID</code>")
        return

    user_id = int(raw_user_id)
    user = await set_user_ban_status(session, user_id, is_banned=False)

    group_unbanned = True
    try:
        await bot.unban_chat_member(
            chat_id=config.RECEIPTS_GROUP_ID,
            user_id=user_id,
            only_if_banned=True,
        )
    except (TelegramBadRequest, TelegramForbiddenError):
        group_unbanned = False

    if not user and not group_unbanned:
        await message.answer(f"Пользователь <code>{user_id}</code> не найден.")
        return

    status = "в боте и админ-группе" if group_unbanned else "в боте"
    await message.answer(
        f"✅ Пользователь <code>{user_id}</code> разблокирован {status}."
    )


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
