from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.crud import (
    get_user_by_tg_id,
    get_user_by_username,
    update_user_balance,
    set_user_ban_status,
    get_user_orders
)
from keyboards.inline_admin import get_user_manage_kb
from states.admin_states import UserSearchState, UserBalanceState
from utils.ui_cleaner import send_or_edit_screen, delete_user_message
from utils.formatters import format_admin_user_card, DIVIDER

router = Router(name="admin_users_mgmt")


@router.callback_query(F.data == "adm_users")
async def start_users_mgmt(call: CallbackQuery, state: FSMContext):
    """Начало поиска пользователя."""
    await state.set_state(UserSearchState.waiting_for_query)
    text = (
        f"👥 <b>Управление клиентами</b>\n"
        f"{DIVIDER}\n"
        f"Отправьте <b>Telegram ID</b> или <b>@username</b> пользователя для поиска:"
    )
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В админку", callback_data="adm_main")]
    ])
    await send_or_edit_screen(call, text, reply_markup=cancel_kb, state=state)
    await call.answer()


@router.message(UserSearchState.waiting_for_query)
async def process_user_search(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    """Поиск пользователя по ID или юзернейму с удалением входящего текста."""
    query = message.text.strip()
    await delete_user_message(message)

    user: User = None
    if query.isdigit():
        user = await get_user_by_tg_id(session, int(query))
    else:
        user = await get_user_by_username(session, query)

    if not user:
        text = (
            f"❌ <b>Пользователь не найден</b>\n"
            f"{DIVIDER}\n"
            f"В базе бота нет клиента с такими данными. Попробуйте еще раз:"
        )
        cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ В админку", callback_data="adm_main")]
        ])
        await send_or_edit_screen(message, text, reply_markup=cancel_kb, state=state, bot=bot)
        return

    await state.clear()
    orders = await get_user_orders(session, user.id, limit=100)
    card_text = format_admin_user_card(user, len(orders))

    await send_or_edit_screen(
        message,
        card_text,
        reply_markup=get_user_manage_kb(user.tg_id, user.is_banned),
        state=state,
        bot=bot
    )


@router.callback_query(F.data.startswith("adm_ban_"))
async def process_ban_user(call: CallbackQuery, session: AsyncSession):
    """Блокировка пользователя."""
    tg_id = int(call.data.split("_")[2])
    user = await set_user_ban_status(session, tg_id, is_banned=True)
    if user:
        await call.answer("Пользователь заблокирован!", show_alert=True)
        orders = await get_user_orders(session, user.id, limit=100)
        card_text = format_admin_user_card(user, len(orders))
        await call.message.edit_text(card_text, parse_mode="HTML", reply_markup=get_user_manage_kb(user.tg_id, is_banned=True))


@router.callback_query(F.data.startswith("adm_unban_"))
async def process_unban_user(call: CallbackQuery, session: AsyncSession):
    """Разблокировка пользователя."""
    tg_id = int(call.data.split("_")[2])
    user = await set_user_ban_status(session, tg_id, is_banned=False)
    if user:
        await call.answer("Пользователь разблокирован!", show_alert=True)
        orders = await get_user_orders(session, user.id, limit=100)
        card_text = format_admin_user_card(user, len(orders))
        await call.message.edit_text(card_text, parse_mode="HTML", reply_markup=get_user_manage_kb(user.tg_id, is_banned=False))


@router.callback_query(F.data.startswith("adm_bal_add_"))
async def start_balance_add(call: CallbackQuery, state: FSMContext):
    """Начало начисления баланса."""
    tg_id = int(call.data.split("_")[3])
    await state.set_state(UserBalanceState.waiting_for_amount)
    await state.update_data(target_tg_id=tg_id, action="add")

    text = f"💰 Введите сумму для <b>начисления</b> пользователю <code>{tg_id}</code> в рублях:"
    await send_or_edit_screen(call, text, state=state)
    await call.answer()


@router.callback_query(F.data.startswith("adm_bal_sub_"))
async def start_balance_sub(call: CallbackQuery, state: FSMContext):
    """Начало списания баланса."""
    tg_id = int(call.data.split("_")[3])
    await state.set_state(UserBalanceState.waiting_for_amount)
    await state.update_data(target_tg_id=tg_id, action="sub")

    text = f"💸 Введите сумму для <b>списания</b> у пользователя <code>{tg_id}</code> в рублях:"
    await send_or_edit_screen(call, text, state=state)
    await call.answer()


@router.message(UserBalanceState.waiting_for_amount)
async def process_balance_change(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    """Сохранение изменения баланса с очисткой сообщения админа."""
    raw = message.text.strip().replace(",", ".")
    await delete_user_message(message)

    try:
        amount = float(raw)
        if amount <= 0:
            raise ValueError
    except ValueError:
        text = "⚠️ Введите корректное положительное число. Например: <code>500</code>"
        await send_or_edit_screen(message, text, state=state, bot=bot)
        return

    data = await state.get_data()
    tg_id = data["target_tg_id"]
    delta = amount if data["action"] == "add" else -amount

    user = await update_user_balance(session, tg_id, delta)
    await state.clear()

    if user:
        action_word = "начислено" if delta > 0 else "списано"
        orders = await get_user_orders(session, user.id, limit=100)
        card_text = format_admin_user_card(user, len(orders))
        res_text = (
            f"✅ <b>Операция выполнена!</b>\n"
            f"Успешно {action_word} <code>{amount:g} ₽</code>.\n\n"
            f"{card_text}"
        )
        await send_or_edit_screen(message, res_text, reply_markup=get_user_manage_kb(user.tg_id, user.is_banned), state=state, bot=bot)
    else:
        await send_or_edit_screen(message, "Ошибка: пользователь не найден.", state=state, bot=bot)
