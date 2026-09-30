from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from database.crud import set_user_ban_status
from keyboards.inline_admin import (
    get_admin_main_kb,
    get_stats_period_kb,
    get_admin_settings_kb,
    get_admin_cities_kb,
    get_showcase_admin_kb,
    InlineKeyboardButton,
)
from keyboards.inline_client import get_bottom_reply_kb, get_main_menu_kb
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
from utils.formatters import format_admin_dashboard, DIVIDER

router = Router(name="admin_base")


# ──────────────────────────────────────────────────────────
#  /unban — разблокировка пользователя
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


# ──────────────────────────────────────────────────────────
#  /admin, /panel — вход в панель
# ──────────────────────────────────────────────────────────

@router.message(Command("admin", "panel"))
async def cmd_admin_panel(message: Message, state: FSMContext, bot: Bot):
    """Вход в панель администратора."""
    await delete_user_message(message)
    await state.clear()

    # Устанавливаем админскую Reply Keyboard + выводим инлайн-дашборд одним сообщением
    sent = await bot.send_message(
        chat_id=message.chat.id,
        text=format_admin_dashboard(),
        parse_mode="HTML",
        reply_markup=get_admin_main_kb(),
        disable_web_page_preview=True,
    )
    # Отдельным шагом — устанавливаем Reply Keyboard (пустое служебное сообщение → удаляем)
    kb_msg = await bot.send_message(
        chat_id=message.chat.id,
        text="🛠️ <b>Панель управления активна.</b> Используйте кнопки ниже.",
        parse_mode="HTML",
        reply_markup=get_admin_reply_kb(),
    )
    await state.update_data({"last_screen_message_id": sent.message_id})


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
async def reply_admin_panel(message: Message, state: FSMContext, bot: Bot):
    """🛠 Панель управления — главное инлайн-меню администратора."""
    await delete_user_message(message)
    await state.clear()
    await send_or_edit_screen(
        message,
        format_admin_dashboard(),
        reply_markup=get_admin_main_kb(),
        state=state,
        bot=bot,
    )


@router.message(F.text == BTN_ADM_USERS)
async def reply_admin_users(message: Message, state: FSMContext, bot: Bot):
    """👥 Пользователи — переход к поиску клиента."""
    await delete_user_message(message)
    await state.set_state(UserSearchState.waiting_for_query)
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В админку", callback_data="adm_main")]
    ])
    await send_or_edit_screen(
        message,
        f"👥 <b>Управление клиентами</b>\n{DIVIDER}\n"
        "Отправьте <b>Telegram ID</b> или <b>@username</b> пользователя для поиска:",
        reply_markup=cancel_kb,
        state=state,
        bot=bot,
    )


@router.message(F.text == BTN_ADM_STATS)
async def reply_admin_stats(message: Message, state: FSMContext, bot: Bot):
    """📊 Статистика — выбор периода аналитики."""
    await delete_user_message(message)
    await state.clear()
    await send_or_edit_screen(
        message,
        f"📊 <b>Статистика и аналитика продаж</b>\n{DIVIDER}\n"
        "Выберите временной период для формирования сводки:",
        reply_markup=get_stats_period_kb(),
        state=state,
        bot=bot,
    )


@router.message(F.text == BTN_ADM_BROADCAST)
async def reply_admin_broadcast(message: Message, state: FSMContext, bot: Bot):
    """📢 Рассылка — начало создания рассылки."""
    await delete_user_message(message)
    await state.set_state(BroadcastState.waiting_for_content)
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="adm_cancel_broadcast")]
    ])
    await send_or_edit_screen(
        message,
        f"📢 <b>Создание рассылки</b>\n{DIVIDER}\n"
        "Отправьте сообщение для рассылки всем пользователям.\n"
        "Поддерживаются текст, фото, видео, документы.",
        reply_markup=cancel_kb,
        state=state,
        bot=bot,
    )


@router.message(F.text == BTN_ADM_CITIES)
async def reply_admin_cities(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    """🏙️ Города — управление городами и районами."""
    await delete_user_message(message)
    await state.clear()
    from database.crud import get_all_cities
    cities = await get_all_cities(session)
    await send_or_edit_screen(
        message,
        f"🏙️ <b>Управление городами и районами</b>\n{DIVIDER}\n"
        f"Всего городов: <b>{len(cities)}</b>",
        reply_markup=get_admin_cities_kb(cities),
        state=state,
        bot=bot,
    )


@router.message(F.text == BTN_ADM_SHOWCASE)
async def reply_admin_showcase(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    """🛍️ Товары — управление витриной."""
    await delete_user_message(message)
    await state.clear()
    from database.crud import get_showcase_products
    products = await get_showcase_products(session)
    await send_or_edit_screen(
        message,
        f"🛍️ <b>Витрина товаров</b>\n{DIVIDER}\n"
        f"Товаров в витрине: <b>{len(products)}</b>",
        reply_markup=get_showcase_admin_kb(products),
        state=state,
        bot=bot,
    )


@router.message(F.text == BTN_ADM_SETTINGS)
async def reply_admin_settings(message: Message, state: FSMContext, bot: Bot):
    """⚙️ Настройки — конфигурация бота."""
    await delete_user_message(message)
    await state.clear()
    cfg = config
    text = (
        f"⚙️ <b>Настройки бота</b>\n"
        f"{DIVIDER}\n"
        "Текущая конфигурация загружается из файла <code>.env</code>.\n\n"
        f"🛟 <b>Поддержка:</b> <code>{cfg.SUPPORT_USERNAME or 'не задано'}</code>\n"
        f"💠 <b>Канал отзывов:</b> <code>{cfg.REVIEWS_CHANNEL or 'не задано'}</code>\n"
        f"📖 <b>FAQ:</b> <code>{cfg.FAQ_URL or 'не задано'}</code>\n"
        f"🧾 <b>Группа чеков:</b> <code>{cfg.RECEIPTS_GROUP_ID}</code>\n"
        f"💳 <b>CryptoBot:</b> {'🟢 подключен' if cfg.CRYPTO_BOT_TOKEN else '⚪ не настроен'}\n"
        f"💳 <b>Банковская оплата:</b> "
        f"{'🟢 подключена' if cfg.TELEGRAM_PAYMENT_PROVIDER_TOKEN else '⚪ не настроена'}\n"
        f"{DIVIDER}\n"
        "Для изменения параметров обновите <code>.env</code> и перезапустите бота."
    )
    await send_or_edit_screen(
        message,
        text,
        reply_markup=get_admin_settings_kb(),
        state=state,
        bot=bot,
    )


@router.message(F.text == BTN_ADM_MAIN_MENU)
async def reply_to_client_menu(message: Message, state: FSMContext, bot: Bot, db_user):
    """◀️ В клиентское меню — возврат к клиентской панели."""
    await delete_user_message(message)
    await state.clear()

    # Показываем клиентское главное меню в чистом виде.
    # Reply Keyboard переключаем на клиентский вариант (с кнопкой /admin для админа).
    # Получаем данные пользователя если есть (middleware может не передавать db_user)
    from handlers.client.start import get_main_banner
    banner = get_main_banner()

    # Переключаем reply-клавиатуру на клиентскую (с доступом /admin для удобства)
    await bot.send_message(
        chat_id=message.chat.id,
        text="👋",
        reply_markup=get_bottom_reply_kb(is_admin=True),
    )

    # Отправляем инлайн-меню клиента
    await send_or_edit_screen(
        message,
        "🍭 <b>Главное меню</b>",
        reply_markup=get_main_menu_kb(db_user),
        photo=banner,
        state=state,
        bot=bot,
    )
