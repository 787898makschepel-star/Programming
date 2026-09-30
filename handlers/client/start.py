import os
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile, ForceReply, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from database.models import User
from database.crud import update_user_balance, attach_referrer, get_referral_stats
from keyboards.inline_client import (
    get_main_menu_kb,
    get_game_reply_kb,
    get_districts_kb,
    get_city_select_kb,
    get_back_to_menu_kb,
    CITY_DISTRICTS,
    InlineKeyboardButton
)
from utils.callback_parser import parse_callback_suffix
from states.client_states import CityState, PromoState
from utils.ui_cleaner import send_or_edit_screen, delete_user_message
from utils.formatters import format_faq, DIVIDER
from handlers.emoji_captcha import send_start_captcha

router = Router(name="client_start")

BANNER_PATH = "assets/main_banner.jpg"
CITY_ALIASES = {
    "ростов": "Ростов-на-Дону",
    "питер": "Санкт-Петербург",
}


def get_start_sticker_id() -> str:
    """Возвращает текущий стартовый стикер из настроек бота."""
    value = getattr(config, "START_STICKER_ID", "") or "CAACAgIAAxkBAAEHFCRqrGcwLKCbKyZpF__HJ9KnVhpwfAACMWoAAi38IEs5Qp_3NDiFkz0E"
    return value.strip() or "CAACAgIAAxkBAAEHFCRqrGcwLKCbKyZpF__HJ9KnVhpwfAACMWoAAi38IEs5Qp_3NDiFkz0E"


def get_main_banner() -> FSInputFile | None:
    """Возвращает основной баннер приветствия."""
    if os.path.exists(BANNER_PATH):
        return FSInputFile(BANNER_PATH)
    return None


@router.message(CommandStart())
@router.message(F.text == "🍭 Главное меню")
async def cmd_start(message: Message, db_user: User, state: FSMContext, bot: Bot, session: AsyncSession):
    """
    Стартовая страница точь-в-точь как на скриншоте:
    - Отправляет постоянную кнопку '🍭 Главное меню' внизу.
    - Выводит фирменный баннер METH WAVE с тюленем и кнопками.
    """
    start_text = message.text or ""
    is_start_command = start_text.startswith("/start")
    if is_start_command:
        db_user.start_count += 1
        db_user.captcha_passed = False
        if not db_user.start_pending:
            db_user.start_pending = True
            await session.commit()
            return

        db_user.start_pending = False
        await session.commit()

    if not db_user.captcha_passed:
        if not is_start_command:
            return
        await state.clear()
        await delete_user_message(message)
        await send_start_captcha(bot, message.chat.id, db_user)
        return

    if not db_user.city:
        await delete_user_message(message)
        await state.clear()
        await state.set_state(CityState.waiting_for_city)
        await state.update_data(onboarding_after_captcha=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text=(
                f"📍 <b>Укажите город</b>\n{DIVIDER}\n"
                "Напишите свой город, чтобы продолжить."
            ),
            parse_mode="HTML",
            reply_markup=ForceReply(
                input_field_placeholder="Напишите свой город",
                selective=True,
            ),
        )
        return

    await delete_user_message(message)
    await state.clear()

    if is_start_command:
        payload = start_text.split(maxsplit=1)[1].strip() if len(start_text.split(maxsplit=1)) > 1 else ""
        if payload.startswith("ref") and payload[3:].isdigit():
            await attach_referrer(session, db_user, int(payload[3:]))

    try:
        await bot.send_sticker(
            chat_id=message.chat.id,
            sticker=get_start_sticker_id(),
            reply_markup=get_game_reply_kb(),
        )
    except Exception as exc:
        logger = __import__("logging").getLogger(__name__)
        logger.debug("Failed to send startup sticker: %s", exc)
        await bot.send_message(
            chat_id=message.chat.id,
            text="🍭",
            reply_markup=get_game_reply_kb(),
        )

    banner = get_main_banner()
    if banner:
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=banner,
            caption=None,
            reply_markup=get_main_menu_kb(db_user),
        )
    else:
        await bot.send_message(
            chat_id=message.chat.id,
            text="🍭 <b>Главное меню</b>",
            parse_mode="HTML",
            reply_markup=get_main_menu_kb(db_user),
            disable_web_page_preview=True,
        )


@router.message(F.text.in_({"🛟 Тех. Поддержка", "💸 Работа без залога"}))
async def handle_game_reply_button(message: Message):
    """Обрабатывает нажатия кнопок игровой клавиатуры."""
    if message.text == "🛟 Тех. Поддержка":
        support_username = str(getattr(config, "SUPPORT_USERNAME", "") or "").strip()
        if support_username.startswith(("https://t.me/", "http://t.me/")):
            support_url = support_username
        else:
            support_url = f"https://t.me/{support_username.lstrip('@')}" if support_username else "https://t.me/"
        await message.answer(
            "🛟 Напишите в техподдержку:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Открыть поддержку", url=support_url)]
                ]
            ),
        )
        return

    support_username = str(getattr(config, "SUPPORT_USERNAME", "") or "").strip()
    if support_username.startswith(("https://t.me/", "http://t.me/")):
        support_url = support_username
    else:
        support_url = f"https://t.me/{support_username.lstrip('@')}" if support_username else "https://t.me/"

    support_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Написать в техподдержку",
                    url=support_url,
                )
            ]
        ]
    )

    await message.answer(
        """Работа с нами. Требуются люди готовые качественно работать и хорошо зарабатывать.

💁‍♀️ Лучшие условия у нас

1. Свободный график работы
2. Выплата зарплаты еженедельно
3. В день до 5 часов Вашего времени
4. Высокий уровень оплаты труда от 700 $ в неделю
5. Полная подготовка к работе, опыт и пол не важен

💦 Условия трудоустройства

1. Устройство по внесению залога.
2. Наработка на залог граффити либо стикерами""",
        reply_markup=support_keyboard,
    )


@router.callback_query(F.data == "to_main_menu")
async def cb_main_menu(call: CallbackQuery, db_user: User, state: FSMContext, bot: Bot):
    """Возврат в главное меню."""
    await state.clear()
    banner = get_main_banner()
    await send_or_edit_screen(
        event=call,
        text="",
        reply_markup=get_main_menu_kb(db_user),
        photo=banner,
        state=state,
        bot=bot
    )
    await call.answer()


# ==========================================
# ВЫБОР ГОРОДА (📍 Город (Москва))
# ==========================================

@router.callback_query(F.data == "client_city")
async def show_city_selection(call: CallbackQuery, db_user: User, state: FSMContext):
    """Показывает клавиатуру выбора города кнопками (не текстом)."""
    current_city = getattr(db_user, "city", "") or "не выбран"
    await state.set_state(CityState.waiting_for_city)
    if not db_user.city:
        await state.update_data(onboarding_after_captcha=True)
    await call.answer()
    text = (
        f"📍 <b>Выбор вашего города</b>\n"
        f"{DIVIDER}\n"
        f"Текущий выбранный город: <b>{current_city}</b>\n\n"
        "Выберите город из списка или напишите его сообщением:"
    )
    await send_or_edit_screen(
        event=call,
        text=text,
        reply_markup=get_city_select_kb(page=0),
        state=state,
    )


@router.callback_query(F.data.startswith("city_page_"))
async def paginate_city_select(call: CallbackQuery, db_user: User, state: FSMContext):
    """Перелистывание страниц списка городов."""
    try:
        page = int((call.data or "").split("city_page_", 1)[1])
    except (IndexError, ValueError):
        page = 0
    current_city = getattr(db_user, "city", "") or "не выбран"
    text = (
        f"📍 <b>Выбор вашего города</b>\n"
        f"{DIVIDER}\n"
        f"Текущий выбранный город: <b>{current_city}</b>\n\n"
        "Выберите город из списка:"
    )
    await send_or_edit_screen(
        event=call,
        text=text,
        reply_markup=get_city_select_kb(page=page),
        state=state,
    )
    await call.answer()


@router.message(CityState.waiting_for_city)
async def process_city_input(message: Message, session: AsyncSession, db_user: User, state: FSMContext, bot: Bot):
    """Сохраняет город из списка, введенный пользователем вручную."""
    city_input = (message.text or "").strip()
    city_by_normalized_name = {
        city.casefold(): city
        for city in CITY_DISTRICTS
    }
    city_by_normalized_name.update(
        {alias: city for alias, city in CITY_ALIASES.items()}
    )
    city = city_by_normalized_name.get(city_input.casefold())

    await delete_user_message(message)

    if city is None:
        await send_or_edit_screen(
            event=message,
            text=(
                "❌ <b>Город не найден</b>\n"
                f"{DIVIDER}\n"
                "Выберите город из списка или напишите точное название:"
            ),
            reply_markup=get_city_select_kb(page=0),
            state=state,
            bot=bot,
        )
        return

    db_user.city = city
    db_user.district = None
    await session.commit()
    await session.refresh(db_user)

    state_data = await state.get_data()
    if state_data.get("onboarding_after_captcha"):
        await state.update_data(onboarding_after_captcha=False)
        try:
            await bot.send_sticker(
                chat_id=message.chat.id,
                sticker=get_start_sticker_id(),
                reply_markup=get_game_reply_kb(),
            )
        except Exception as exc:
            logger = __import__("logging").getLogger(__name__)
            logger.debug("Failed to send startup sticker after city selection: %s", exc)
            await bot.send_message(
                chat_id=message.chat.id,
                text="🍭",
                reply_markup=get_game_reply_kb(),
            )
        await send_or_edit_screen(
            event=message,
            text="",
            reply_markup=get_main_menu_kb(db_user),
            photo=get_main_banner(),
            state=state,
            bot=bot,
        )
        await state.set_state(None)
        return

    await state.clear()

    await send_or_edit_screen(
        event=message,
        text=(
            f"📍 <b>{city}</b>\n"
            f"{DIVIDER}\n"
            "Теперь выберите район, в котором будет оформляться заказ:"
        ),
        reply_markup=get_districts_kb(city),
        photo=get_main_banner(),
        state=state,
        bot=bot,
    )


@router.callback_query(F.data.startswith("set_city_"))
async def process_city_choice(call: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext):
    """Сохраняет город и показывает районы только этого города."""
    new_city = parse_callback_suffix(call.data, "set_city_")
    if not new_city:
        await call.answer("Не удалось определить город.", show_alert=True)
        return

    if new_city not in CITY_DISTRICTS:
        await call.answer("Город временно недоступен.", show_alert=True)
        return

    db_user.city = new_city
    db_user.district = None
    await session.commit()
    await session.refresh(db_user)

    await call.answer(f"Город выбран: {new_city}")
    await send_or_edit_screen(
        event=call,
        text=(
            f"📍 <b>{new_city}</b>\n"
            f"{DIVIDER}\n"
            "Теперь выберите район, в котором будет оформляться заказ:"
        ),
        reply_markup=get_districts_kb(new_city),
        photo=get_main_banner(),
        state=state,
    )


# ==========================================
# ПРОМОКОДЫ (🎁 Промокод)
# ==========================================

@router.callback_query(F.data == "client_promo")
async def start_promo_input(call: CallbackQuery, state: FSMContext):
    """Запрос ввода промокода."""
    await state.set_state(PromoState.waiting_for_code)
    text = (
        f"🎁 <b>Активация промокода</b>\n"
        f"{DIVIDER}\n"
        f"Введите промокод в поле ввода сообщением.\n\n"
        f"💡 <i>Подсказка: на приветственном баннере действует промокод</i> <code>#WILLIWONKA</code> <i>на 300₽!</i>"
    )
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Отмена", callback_data="to_main_menu")]
    ])
    await send_or_edit_screen(call, text, reply_markup=cancel_kb, state=state)
    await call.answer()


@router.message(PromoState.waiting_for_code)
async def process_promo_code(message: Message, state: FSMContext, session: AsyncSession, db_user: User, bot: Bot):
    """Обработка ввода промокода."""
    if message.text is None:
        await send_or_edit_screen(
            message,
            "❌ <b>Неверный формат промокода</b>\n"
            f"{DIVIDER}\n"
            "Введите промокод текстом.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_main_menu")]
            ]),
            state=state,
            bot=bot,
        )
        await state.clear()
        return

    code = message.text.strip().upper().replace("#", "")
    await delete_user_message(message)

    used = db_user.used_promos.split(",") if db_user.used_promos else []

    if code == "WILLIWONKA":
        if "WILLIWONKA" in used:
            text = (
                f"⚠️ <b>Промокод уже был активирован</b>\n"
                f"{DIVIDER}\n"
                f"Вы уже получали 300₽ по промокоду <code>#WILLIWONKA</code>."
            )
        else:
            used.append("WILLIWONKA")
            db_user.used_promos = ",".join(used)
            db_user.balance = round(db_user.balance + 300.0, 2)
            await session.commit()
            await session.refresh(db_user)

            text = (
                f"🎉 <b>Промокод успешно активирован!</b>\n"
                f"{DIVIDER}\n"
                f"💰 На ваш баланс зачислено: <b>+300 ₽</b>\n"
                f"💳 Текущий баланс: <b>{db_user.balance:g} ₽</b>\n\n"
                f"Приятных покупок в магазине WILLI WONKA!"
            )
    else:
        text = (
            f"❌ <b>Неверный промокод</b>\n"
            f"{DIVIDER}\n"
            f"Промокод не найден или срок его действия истек."
        )

    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_main_menu")]
    ])
    await send_or_edit_screen(message, text, reply_markup=cancel_kb, state=state, bot=bot)
    await state.clear()


# ==========================================
# ПАРТНЕРСКАЯ ПРОГРАММА (🤝 Пригласи друга)
# ==========================================

@router.callback_query(F.data == "client_ref")
async def show_referral_system(call: CallbackQuery, db_user: User, bot: Bot, state: FSMContext, session: AsyncSession):
    """Партнерская ссылка и условия."""
    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref{db_user.tg_id}"
    referrals_count, referral_earnings = await get_referral_stats(session, db_user.id)

    text = (
        f"🤝 <b>Реферальная программа WILLI WONKA</b>\n"
        f"{DIVIDER}\n"
        f"Приглашайте друзей и зарабатывайте <b>5%</b> с каждой их покупки на свой баланс!\n\n"
        f"🔗 <b>Ваша личная ссылка:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"👥 Приглашено друзей: <b>{referrals_count} чел.</b>\n"
        f"💵 Заработано с рефералов: <b>{referral_earnings:g} ₽</b>"
    )
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_main_menu")]
    ])
    await send_or_edit_screen(call, text, reply_markup=back_kb, state=state)
    await call.answer()


@router.callback_query(F.data == "client_faq")
async def cb_faq(call: CallbackQuery, state: FSMContext):
    """Отображение раздела FAQ."""
    text = format_faq()
    await send_or_edit_screen(
        event=call,
        text=text,
        reply_markup=get_back_to_menu_kb(),
        state=state
    )
    await call.answer()
