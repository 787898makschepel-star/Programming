import os
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.crud import update_user_balance, attach_referrer, get_referral_stats
from keyboards.inline_client import (
    get_main_menu_kb,
    get_city_select_kb,
    get_districts_kb,
    get_bottom_reply_kb,
    get_back_to_menu_kb,
    CITY_DISTRICTS
)
from states.client_states import PromoState
from utils.ui_cleaner import send_or_edit_screen, delete_user_message
from utils.formatters import format_faq, DIVIDER
from config import config

router = Router(name="client_start")

BANNER_PATH = "assets/main_banner.jpg"


def get_main_banner() -> FSInputFile | None:
    """Возвращает баннер с тюленем METH WAVE, если он существует."""
    if os.path.exists(BANNER_PATH):
        return FSInputFile(BANNER_PATH)
    return None


@router.message(CommandStart())
@router.message(F.text == "🌊 Главное меню")
async def cmd_start(message: Message, db_user: User, state: FSMContext, bot: Bot, session: AsyncSession):
    """
    Стартовая страница точь-в-точь как на скриншоте:
    - Отправляет постоянную кнопку '🌊 Главное меню' внизу.
    - Выводит фирменный баннер METH WAVE с тюленем и кнопками.
    """
    await delete_user_message(message)
    await state.clear()

    if message.text and message.text.startswith("/start"):
        payload = message.text.split(maxsplit=1)[1].strip() if len(message.text.split(maxsplit=1)) > 1 else ""
        if payload.startswith("ref") and payload[3:].isdigit():
            await attach_referrer(session, db_user, int(payload[3:]))

    # Отправляем закрепляемую нижнюю кнопку
    try:
        await bot.send_message(
            chat_id=message.chat.id,
            text="🦭",
            reply_markup=get_bottom_reply_kb(db_user.tg_id in config.ADMIN_IDS)
        )
    except Exception:
        pass

    banner = get_main_banner()
    # Текст на баннере уже содержит приветствие, поэтому подпись лаконичная или пустая
    caption = ""
    await send_or_edit_screen(
        event=message,
        text=caption,
        reply_markup=get_main_menu_kb(db_user),
        photo=banner,
        state=state,
        bot=bot
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
# ВЫБОР ГОРОДА (💦 Город (Москва))
# ==========================================

@router.callback_query(F.data == "client_city")
async def show_city_selection(call: CallbackQuery, db_user: User, state: FSMContext):
    """Выбор текущего города."""
    current_city = getattr(db_user, "city", "") or "не выбран"
    text = (
        f"💦 <b>Выбор вашего города</b>\n"
        f"{DIVIDER}\n"
        f"Текущий выбранный город: <b>{current_city}</b>\n\n"
        f"Выберите город, чтобы затем указать район для заказа:"
    )
    await send_or_edit_screen(call, text, reply_markup=get_city_select_kb(), state=state)
    await call.answer()


@router.callback_query(F.data.startswith("set_city_"))
async def process_city_choice(call: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext):
    """Сохраняет город и показывает районы только этого города."""
    new_city = call.data.replace("set_city_", "")
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
        f"💡 <i>Подсказка: на приветственном баннере действует промокод</i> <code>#METHWAVE</code> <i>на 300₽!</i>"
    )
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Отмена", callback_data="to_main_menu")]
    ])
    await send_or_edit_screen(call, text, reply_markup=cancel_kb, state=state)
    await call.answer()


@router.message(PromoState.waiting_for_code)
async def process_promo_code(message: Message, state: FSMContext, session: AsyncSession, db_user: User, bot: Bot):
    """Обработка ввода промокода."""
    code = message.text.strip().upper().replace("#", "")
    await delete_user_message(message)

    used = db_user.used_promos.split(",") if db_user.used_promos else []

    if code == "METHWAVE":
        if "METHWAVE" in used:
            text = (
                f"⚠️ <b>Промокод уже был активирован</b>\n"
                f"{DIVIDER}\n"
                f"Вы уже получали 300₽ по промокоду <code>#METHWAVE</code>."
            )
        else:
            used.append("METHWAVE")
            db_user.used_promos = ",".join(used)
            db_user.balance = round(db_user.balance + 300.0, 2)
            await session.commit()
            await session.refresh(db_user)

            text = (
                f"🎉 <b>Промокод успешно активирован!</b>\n"
                f"{DIVIDER}\n"
                f"💰 На ваш баланс зачислено: <b>+300 ₽</b>\n"
                f"💳 Текущий баланс: <b>{db_user.balance:g} ₽</b>\n\n"
                f"Приятных покупок в магазине METH WAVE!"
            )
    else:
        text = (
            f"❌ <b>Неверный промокод</b>\n"
            f"{DIVIDER}\n"
            f"Промокод не найден или срок его действия истек."
        )

    await state.clear()
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_main_menu")]
    ])
    await send_or_edit_screen(message, text, reply_markup=cancel_kb, state=state, bot=bot)


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
        f"🤝 <b>Реферальная программа METH WAVE</b>\n"
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
