from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from database.crud import set_user_ban_status
from keyboards.inline_admin import (
    get_admin_main_kb,
    get_stats_period_kb,
    get_admin_settings_kb,
    InlineKeyboardButton,
)
from keyboards.inline_client import get_bottom_reply_kb
from keyboards.reply_admin import (
    get_admin_reply_kb,
    BTN_ADM_PANEL,
    BTN_ADM_USERS,
    BTN_ADM_STATS,
    BTN_ADM_BROADCAST,
    BTN_ADM_CITIES,
    BTN_ADM_SHOWCASE,
    BTN_ADM_SETTINGS,
    BTN_ADM_MAIN_MENU,
)
from states.admin_states import UserSearchState, BroadcastState
from utils.ui_cleaner import send_or_edit_screen, delete_user_message
from utils.formatters import format_admin_dashboard, format_admin_stats, DIVIDER
from aiogram.types import InlineKeyboardMarkup

router = Router(name="admin_base")


# ──────────────────────────────────────────────────────────
#  /admin, /panel — вход в панель
# ──────────────────────────────────────────────────────────

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
    """Вход в панель администратора: удаляет команду и выводит чистый экран."""
    await delete_user_message(message)
    await state.clear()
    text = format_admin_dashboard()
    await message.answer(
        "🛠️ <b>Добро пожаловать в панель управления!</b>\n"
        "Используйте кнопки ниже для навигации.",
        reply_markup=get_admin_reply_kb(),
    )
    await send_or_edit_screen(message, text, reply_markup=get_admin_main_kb(), state=state)


@router.callback_query(F.data == "adm_main")
async def cb_admin_main(call: CallbackQuery, state: FSMContext):
    """Возврат в главное меню панели администратора."""
    await state.clear()
    text = format_admin_dashboard()
    await send_or_edit_screen(call, text, reply_markup=get_admin_main_kb(), state=state)
    await call.answer()


# ──────────────────────────────────────────────────────────
#  Reply Keyboard — обработчики кнопок
# ──────────────────────────────────────────────────────────

@router.message(F.text == BTN_ADM_PANEL)
async def reply_admin_panel(message: Message, state: FSMContext):
    """🛠 Панель управления — главное инлайн-меню администратора."""
    await state.clear()
    text = format_admin_dashboard()
    await send_or_edit_screen(message, text, reply_markup=get_admin_main_kb(), state=state)


@router.message(F.text == BTN_ADM_USERS)
async def reply_admin_users(message: Message, state: FSMContext):
    """👥 Пользователи — переход к поиску клиента."""
    await state.set_state(UserSearchState.waiting_for_query)
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В админку", callback_data="adm_main")]
    ])
    text = (
        f"👥 <b>Управление клиентами</b>\n"
        f"{DIVIDER}\n"
        f"Отправьте <b>Telegram ID</b> или <b>@username</b> пользователя для поиска:"
    )
    await send_or_edit_screen(message, text, reply_markup=cancel_kb, state=state)


@router.message(F.text == BTN_ADM_STATS)
async def reply_admin_stats(message: Message, state: FSMContext):
    """📊 Статистика — выбор периода аналитики."""
    await state.clear()
    text = (
        f"📊 <b>Статистика и аналитика продаж</b>\n"
        f"{DIVIDER}\n"
        f"Выберите временной период для формирования сводки:"
    )
    await send_or_edit_screen(message, text, reply_markup=get_stats_period_kb(), state=state)


@router.message(F.text == BTN_ADM_BROADCAST)
async def reply_admin_broadcast(message: Message, state: FSMContext):
    """📢 Рассылка — начало создания рассылки."""
    await state.set_state(BroadcastState.waiting_for_content)
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="adm_cancel_broadcast")]
    ])
    text = (
        f"📢 <b>Создание рассылки</b>\n"
        f"{DIVIDER}\n"
        "Отправьте сообщение для рассылки всем пользователям.\n"
        "Поддерживаются текст, фото, видео, документы."
    )
    await send_or_edit_screen(message, text, reply_markup=cancel_kb, state=state)


@router.message(F.text == BTN_ADM_CITIES)
async def reply_admin_cities(message: Message, state: FSMContext, session: AsyncSession):
    """🏙️ Города — управление городами и районами."""
    await state.clear()
    from database.crud import get_all_cities
    cities = await get_all_cities(session)
    text = (
        f"🏙️ <b>Управление городами и районами</b>\n"
        f"{DIVIDER}\n"
        f"Всего городов: <b>{len(cities)}</b>"
    )
    await send_or_edit_screen(message, text, reply_markup=get_admin_cities_kb(cities), state=state)


@router.message(F.text == BTN_ADM_SHOWCASE)
async def reply_admin_showcase(message: Message, state: FSMContext, session: AsyncSession):
    """🛍️ Товары — управление витриной."""
    await state.clear()
    from database.crud import get_showcase_products
    products = await get_showcase_products(session)
    from keyboards.inline_admin import get_showcase_admin_kb
    text = (
        f"🛍️ <b>Витрина товаров</b>\n"
        f"{DIVIDER}\n"
        f"Товаров в витрине: <b>{len(products)}</b>"
    )
    await send_or_edit_screen(message, text, reply_markup=get_showcase_admin_kb(products), state=state)


@router.message(F.text == BTN_ADM_SETTINGS)
async def reply_admin_settings(message: Message, state: FSMContext):
    """⚙️ Настройки — конфигурация бота."""
    await state.clear()
    from config import config as cfg
    text = (
        f"⚙️ <b>Настройки бота</b>\n"
        f"{DIVIDER}\n"
        "Текущая конфигурация загружается из файла <code>.env</code>.\n\n"
        f"🛟 <b>Поддержка:</b> <code>{cfg.SUPPORT_USERNAME or 'не задано'}</code>\n"
        f"💠 <b>Канал отзывов:</b> <code>{cfg.REVIEWS_CHANNEL or 'не задано'}</code>\n"
        f"📖 <b>FAQ:</b> <code>{cfg.FAQ_URL or 'не задано'}</code>\n"
        f"🧾 <b>Группа чеков:</b> <code>{cfg.RECEIPTS_GROUP_ID}</code>\n"
        f"💳 <b>CryptoBot:</b> {'🟢 подключен' if cfg.CRYPTO_BOT_TOKEN else '⚪ не настроен'}\n"
        f"💳 <b>Банковская оплата:</b> {'🟢 подключена' if cfg.TELEGRAM_PAYMENT_PROVIDER_TOKEN else '⚪ не настроена'}\n"
        f"{DIVIDER}\n"
        "Для изменения параметров обновите <code>.env</code> и перезапустите бота."
    )
    await send_or_edit_screen(message, text, reply_markup=get_admin_settings_kb(), state=state)


@router.message(F.text == BTN_ADM_MAIN_MENU)
async def reply_to_client_menu(message: Message, state: FSMContext):
    """◀️ В клиентское меню — возврат к клиентской панели."""
    await state.clear()
    from keyboards.inline_client import get_main_menu_kb
    await message.answer(
        "◀️ <b>Клиентское меню</b>",
        reply_markup=get_bottom_reply_kb(is_admin=True),
    )
    await send_or_edit_screen(
        message,
        "👋 Главное меню",
        reply_markup=get_main_menu_kb(),
        state=state,
    )
