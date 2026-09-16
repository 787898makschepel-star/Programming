from aiogram import Router, F, Bot
from aiogram.types import (
    CallbackQuery,
    Message,
    PreCheckoutQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LabeledPrice
)
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, PaymentStatus
from database.crud import (
    update_user_balance,
    create_transaction,
    get_transaction_by_id,
    approve_receipt_transaction as complete_transaction
)
from services.telegram_stars import TelegramStarsService
from services.cryptobot import CryptoBotService
from keyboards.inline_client import get_back_to_menu_kb
from utils.ui_cleaner import send_or_edit_screen
from utils.formatters import DIVIDER
from config import config

router = Router(name="payments_router")


# ==========================================
# TELEGRAM STARS (XTR) ОПЛАТА
# ==========================================

@router.callback_query(F.data.startswith("topup_stars_"))
async def start_stars_payment(call: CallbackQuery, bot: Bot, session: AsyncSession, db_user: User):
    """Выставление счета в Telegram Stars."""
    amount_rub = float(call.data.split("_")[2])
    stars_amount = max(1, int(amount_rub))

    tx = await create_transaction(
        session=session,
        user_id=db_user.id,
        amount=amount_rub,
        payment_system="telegram_stars",
        invoice_id=f"stars_{call.from_user.id}_{stars_amount}"
    )

    stars_service = TelegramStarsService(bot)
    await stars_service.create_invoice(
        user_id=call.from_user.id,
        amount=stars_amount,
        title="Пополнение баланса магазина",
        description=f"Пополнение баланса аккаунта на {amount_rub:g} ₽",
        payload=f"tx_{tx.id}"
    )
    await call.answer("⭐️ Счет на оплату Stars отправлен в диалог!", show_alert=False)


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    """Обязательное подтверждение готовности принять платеж Telegram."""
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message, session: AsyncSession, db_user: User, state: FSMContext, bot: Bot):
    """Обработка успешного платежа."""
    payment_info = message.successful_payment
    payload = payment_info.invoice_payload

    if payload.startswith("tx_"):
        tx_id = int(payload.replace("tx_", ""))
        tx = await complete_transaction(session, tx_id)
        if tx:
            text = (
                f"🎉 <b>Баланс успешно пополнен!</b>\n"
                f"{DIVIDER}\n"
                f"💰 Зачислено: <code>+{tx.amount:g} ₽</code>\n"
                f"💳 Текущий баланс: <code>{db_user.balance:g} ₽</code>\n\n"
                f"<i>Вы можете перейти в каталог и оформить заказ.</i>"
            )
            await send_or_edit_screen(message, text, reply_markup=get_back_to_menu_kb(), state=state, bot=bot)
            return

    total_amount = payment_info.total_amount
    await update_user_balance(session, message.from_user.id, float(total_amount))
    text = f"🎉 <b>Оплата принята!</b>\nЗачислено <code>{total_amount} ₽</code> на ваш баланс."
    await send_or_edit_screen(message, text, reply_markup=get_back_to_menu_kb(), state=state, bot=bot)


# ==========================================
# CRYPTOBOT ОПЛАТА
# ==========================================

@router.callback_query(F.data.startswith("topup_crypto_"))
async def start_crypto_payment(call: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext):
    """Создание инвойса через CryptoBot в Single-Screen окне."""
    amount_rub = float(call.data.split("_")[2])

    if not config.CRYPTO_BOT_TOKEN:
        text = (
            f"⚠️ <b>CryptoBot временно недоступен</b>\n"
            f"{DIVIDER}\n"
            f"Пожалуйста, выберите оплату через Telegram Stars или обратитесь к администратору."
        )
        await call.answer("CryptoBot не настроен администратором.", show_alert=True)
        return

    crypto_service = CryptoBotService()
    invoice_data = await crypto_service.create_invoice(
        user_id=call.from_user.id,
        amount=amount_rub,
        title="Пополнение баланса",
        description=f"Пополнение баланса пользователя {call.from_user.id}",
        payload=f"user_{db_user.id}_{amount_rub}"
    )

    if "error" in invoice_data:
        await call.answer(f"Ошибка: {invoice_data['error']}", show_alert=True)
        return

    pay_url = invoice_data["pay_url"]
    invoice_id = str(invoice_data["invoice_id"])

    tx = await create_transaction(
        session=session,
        user_id=db_user.id,
        amount=amount_rub,
        payment_system="cryptobot",
        invoice_id=invoice_id
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Перейти к оплате в CryptoBot", url=pay_url)],
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_crypto_{tx.id}_{invoice_id}")],
        [InlineKeyboardButton(text="⬅️ Назад в профиль", callback_data="client_profile")]
    ])

    text = (
        f"💎 <b>Оплата через CryptoBot</b>\n"
        f"{DIVIDER}\n"
        f"Сумма к оплате: <code>{amount_rub:g} ₽</code> (USDT / TON / BTC)\n"
        f"Номер счета: <code>#{invoice_id}</code>\n\n"
        f"1. Нажмите «Перейти к оплате».\n"
        f"2. Подтвердите транзакцию в боте.\n"
        f"3. Нажмите «Проверить оплату» для мгновенного зачисления."
    )
    await send_or_edit_screen(call, text, reply_markup=kb, state=state)
    await call.answer()


@router.callback_query(F.data.startswith("check_crypto_"))
async def check_crypto_status(call: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Проверка оплаты инвойса CryptoBot."""
    parts = call.data.split("_")
    tx_id = int(parts[2])
    invoice_id = parts[3]

    crypto_service = CryptoBotService()
    is_paid = await crypto_service.verify_payment(invoice_id)

    if is_paid:
        tx = await complete_transaction(session, tx_id)
        text = (
            f"🎉 <b>Платеж подтвержден!</b>\n"
            f"{DIVIDER}\n"
            f"💰 Зачислено: <code>+{tx.amount:g} ₽</code>\n"
            f"Спасибо за пополнение баланса!"
        )
        await send_or_edit_screen(call, text, reply_markup=get_back_to_menu_kb(), state=state)
        await call.answer("Платеж успешно зачислен!", show_alert=True)
    else:
        await call.answer("⚠️ Средства пока не поступили. Подождите пару секунд и проверьте снова.", show_alert=True)


# ==========================================
# КАРТА / ЮKASSA
# ==========================================

@router.callback_query(F.data.startswith("topup_card_"))
async def start_card_payment(call: CallbackQuery, bot: Bot, session: AsyncSession, db_user: User, state: FSMContext):
    """Оплата банковской картой."""
    amount_rub = float(call.data.split("_")[2])

    if not config.TELEGRAM_PAYMENT_PROVIDER_TOKEN:
        text = (
            f"💳 <b>Оплата банковской картой / СБП</b>\n"
            f"{DIVIDER}\n"
            f"Для прямой оплаты на сумму <b>{amount_rub:g} ₽</b> "
            f"напишите нашему оператору: {config.SUPPORT_USERNAME}.\n\n"
            f"<i>Оператор отправит прямые реквизиты СБП и сразу зачислит баланс.</i>"
        )
        back_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад в профиль", callback_data="client_profile")]
        ])
        await send_or_edit_screen(call, text, reply_markup=back_kb, state=state)
        await call.answer()
        return

    tx = await create_transaction(
        session=session,
        user_id=db_user.id,
        amount=amount_rub,
        payment_system="card",
        invoice_id=f"card_{db_user.id}_{amount_rub}"
    )

    prices = [LabeledPrice(label="Пополнение баланса", amount=int(amount_rub * 100))]
    await bot.send_invoice(
        chat_id=call.from_user.id,
        title="Пополнение баланса",
        description=f"Пополнение баланса в магазине на {amount_rub:g} ₽",
        payload=f"tx_{tx.id}",
        provider_token=config.TELEGRAM_PAYMENT_PROVIDER_TOKEN,
        currency="RUB",
        prices=prices
    )
    await call.answer()
