import os
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, FSInputFile
from aiogram.fsm.context import FSMContext
from keyboards.inline_client import InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, ProductType
from database.crud import get_user_orders, get_order_by_id, update_user_balance, create_transaction
from keyboards.inline_client import (
    get_balance_methods_kb,
    get_crypto_wallet_kb,
    get_crypto_networks_kb,
    get_order_history_kb,
    get_back_to_menu_kb
)
from states.client_states import CryptoTxState
from utils.ui_cleaner import send_or_edit_screen, delete_user_message
from utils.formatters import format_order_details, DIVIDER
from config import config
from utils.callback_parser import parse_callback_suffix, parse_callback_int

router = Router(name="client_profile")

BANNER_PATH = "assets/main_banner.jpg"


def get_main_banner() -> FSInputFile | None:
    """Возвращает баннер магазина с тюленем."""
    if os.path.exists(BANNER_PATH):
        return FSInputFile(BANNER_PATH)
    return None


# ==========================================
# ЭКРАН ВЫБОРА СПОСОБА ПОПОЛНЕНИЯ (СКРИНШОТ 1)
# ==========================================

@router.callback_query(F.data == "client_profile")
async def show_balance_methods(call: CallbackQuery, state: FSMContext):
    """
    Экран пополнения баланса точь-в-точь как на скриншоте 1:
    - Баннер с тюленем
    - Подпись: '💰 Выберите способ пополнения:'
    - Кнопки:
      👨‍💻 Через оператора [24/7]
      💲 Криптовалюта [АВТО]
    🍭 Главное меню
    """
    await state.clear()
    banner = get_main_banner()
    caption = "💰 Выберите способ пополнения:"

    await send_or_edit_screen(
        event=call,
        text=caption,
        reply_markup=get_balance_methods_kb(),
        photo=banner,
        state=state
    )
    await call.answer()


# ==========================================
# ВЫБОР СЕТИ USDT
# ==========================================

@router.callback_query(F.data == "topup_crypto_auto")
async def show_crypto_screen(call: CallbackQuery, state: FSMContext):
    """Предлагает выбрать сеть для перевода USDT."""
    await state.clear()
    caption = (
        f"💲 <b>Пополнение баланса в USDT</b>\n"
        f"{DIVIDER}\n"
        f"Выберите сеть, в которой будете отправлять USDT.\n\n"
        f"⚠️ Сеть отправки должна точно совпадать с выбранной сетью."
    )

    await send_or_edit_screen(
        event=call,
        text=caption,
        reply_markup=get_crypto_networks_kb(),
        photo=get_main_banner(),
        state=state
    )
    await call.answer()


MANUAL_CRYPTO_METHODS = {
    "usdt_trc20": ("USDT · TRC20", "USDT", "TRC20 (Tron)", "USDT_TRC20_ADDRESS"),
    "usdt_erc20": ("USDT · ERC20", "USDT", "ERC20 (Ethereum)", "USDT_ERC20_ADDRESS"),
    "usdt_bep20": ("USDT · BEP20", "USDT", "BEP20 (BNB Smart Chain)", "USDT_BEP20_ADDRESS"),
}


@router.callback_query(F.data.startswith("topup_manual_"))
async def show_manual_crypto_screen(call: CallbackQuery, state: FSMContext):
    """Показывает реквизиты выбранной сети для ручной проверки платежа."""
    method_key = parse_callback_suffix(call.data, "topup_manual_")
    if not method_key:
        await call.answer("Способ оплаты временно недоступен.", show_alert=True)
        return

    method = MANUAL_CRYPTO_METHODS.get(method_key)
    if not method:
        await call.answer("Способ оплаты временно недоступен.", show_alert=True)
        return

    title, currency, network, wallet_setting = method
    wallet = getattr(config, wallet_setting)
    await state.set_state(CryptoTxState.waiting_for_receipt)
    caption = (
        f"💳 <b>Пополнение баланса · {title}</b>\n"
        f"{DIVIDER}\n"
        f"🌐 Сеть: <code>{network}</code>\n"
        f"💰 Валюта: <code>{currency}</code>\n\n"
        f"📋 <b>Адрес для перевода</b> (нажмите, чтобы скопировать):\n"
        f"<code>{wallet}</code>\n\n"
        f"⚠️ Отправляйте <b>только USDT</b> через указанную сеть. Перевод в другой сети или другой монеты может быть потерян.\n\n"
        f"1. Отправьте нужную сумму на адрес выше.\n"
        f"2. Ответным сообщением пришлите сумму и TxID либо фото/скриншот чека.\n"
        f"3. После проверки администратор зачислит средства на ваш баланс."
    )
    await send_or_edit_screen(
        call,
        caption,
        reply_markup=get_crypto_wallet_kb(),
        photo=get_main_banner(),
        state=state,
    )
    await call.answer()


# ==========================================
# МОИ ПОКУПКИ (ИСТОРИЯ ЗАКАЗОВ)
# ==========================================

@router.callback_query(F.data == "profile_orders")
async def show_orders_history(call: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext):
    """История покупок пользователя."""
    orders = await get_user_orders(session, db_user.id, limit=20)
    banner = get_main_banner()

    if not orders:
        caption = (
            f"🛒 <b>История покупок пуста</b>\n"
            f"{DIVIDER}\n"
            f"У вас еще нет совершенных покупок. Перейдите в каталог, чтобы выбрать товар!"
        )
        await send_or_edit_screen(call, caption, reply_markup=get_back_to_menu_kb(), photo=banner, state=state)
        await call.answer()
        return

    caption = (
        f"🛒 <b>История ваших покупок</b>\n"
        f"{DIVIDER}\n"
        f"Нажмите на интересующий заказ для повторного просмотра данных:"
    )
    await send_or_edit_screen(call, caption, reply_markup=get_order_history_kb(orders), photo=banner, state=state)
    await call.answer()


@router.callback_query(F.data.startswith("view_order_"))
async def view_single_order(call: CallbackQuery, session: AsyncSession, bot: Bot, state: FSMContext):
    """Просмотр конкретного заказа."""
    order_id = parse_callback_int(call.data, "view_order_")
    if order_id is None:
        await call.answer("Заказ не найден.", show_alert=True)
        return

    order = await get_order_by_id(session, order_id)

    if not order:
        await call.answer("Заказ не найден.", show_alert=True)
        return

    text = format_order_details(order)
    banner = get_main_banner()
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡️ К списку покупок", callback_data="profile_orders")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_main_menu")]
    ])

    if order.product and order.product.product_type == ProductType.FILE and order.product.file_id:
        await send_or_edit_screen(call, text, reply_markup=back_kb, photo=banner, state=state)
        await bot.send_document(
            chat_id=call.from_user.id,
            document=order.product.file_id,
            caption=f"Файл к заказу #{order.id}"
        )
    else:
        await send_or_edit_screen(call, text, reply_markup=back_kb, photo=banner, state=state)

    await call.answer()
