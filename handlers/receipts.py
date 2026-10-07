import logging
import random
import re
from datetime import datetime
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    FSInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from sqlalchemy.ext.asyncio import AsyncSession

from config import config, get_receipts_chat_ids
from keyboards.inline_admin import InlineKeyboardButton
from database.models import User, PaymentStatus, Transaction
from database.crud import (
    create_transaction,
    get_transaction_by_id,
    approve_receipt_transaction,
    reject_receipt_transaction,
    get_user_by_tg_id,
)
from states.client_states import CryptoTxState
from states.admin_states import AdminReceiptState
from utils.ui_cleaner import send_or_edit_screen, delete_user_message
from utils.formatters import DIVIDER
from utils.callback_parser import parse_callback_int
from services.exchange_rate import get_usdt_rub_rate

logger = logging.getLogger(__name__)

router = Router(name="receipts_router")

# {admin_id: {"tx_id": int, "chat_id": int, "receipt_msg_id": int, "prompt_msg_id": int}}
PENDING_APPROVALS: dict = {}


def _gen_receipt_code() -> int:
    """Генерирует случайный 6-значный код чека для пользователя."""
    return random.randint(100000, 999999)

_BANNER_PATH = "assets/main_banner.jpg"


def _get_banner() -> Optional[FSInputFile]:
    """Возвращает FSInputFile для основного баннера или None."""
    import os
    if os.path.exists(_BANNER_PATH):
        return FSInputFile(_BANNER_PATH)
    return None


# ============================================================
# ФОРМАТИРОВАНИЕ КАРТОЧКИ ЧЕКА
# ============================================================

def _get_receipt_code(tx: Transaction, fallback: int) -> str:
    """Получить сохраненный шестизначный номер заявки."""
    if tx.payment_system == "usdt_receipt" and tx.invoice_id and tx.invoice_id.isdigit():
        return tx.invoice_id.zfill(6)
    return str(fallback).zfill(6)


def _build_receipt_card(
    receipt_code: str,
    user: User,
    comment: str,
    time_str: str,
    status: str = "pending",
    amount_rub: float = 0.0,
    amount_usdt: float = 0.0,
    rate: float = 0.0,
    network: str = "USDT",
    admin_name: str = ""
) -> str:
    """Единственный источник разметки карточки чека — используется в группе чеков и логах."""
    username_str = f"@{user.username}" if user.username else "—"

    if status == "pending":
        header = f"🟡 ЗАЯВКА #{receipt_code} · ОЖИДАЕТ"
        if amount_rub > 0:
            footer = (
                f"\n\n<i>👆 Нажмите «✅ Подтвердить ({amount_rub:g} ₽)» для мгновенного зачисления,\n"
                f"«✏️ Изменить сумму» или «❌ Отклонить».</i>"
            )
        else:
            footer = (
                f"\n\n<i>👆 Нажмите «✅ Подтвердить» и введите сумму в рублях,\n"
                f"или «❌ Отклонить» для отмены.</i>"
            )
        balance_line = f"💳 <b>Баланс до:</b> <code>{user.balance:g} ₽</code>"
    elif status == "approved":
        header = f"✅ ЗАЯВКА #{receipt_code} · ПОДТВЕРЖДЕНА"
        footer = (
            f"\n\n{'─' * 24}\n"
            f"✅ <b>Зачислено на баланс:</b> <code>+{amount_rub:g} ₽</code>\n"
            f"💳 <b>Новый баланс:</b> <code>{user.balance:g} ₽</code>\n"
            f"👤 <b>Подтвердил:</b> {admin_name}\n"
            f"🕒 <b>Время:</b> {time_str}"
        )
        balance_line = f"💳 <b>Баланс до:</b> <code>{round(user.balance - amount_rub, 2):g} ₽</code>"
    else:  # rejected
        header = f"❌ ЗАЯВКА #{receipt_code} · ОТКЛОНЕНА"
        footer = (
            f"\n\n{'─' * 24}\n"
            f"❌ <b>Отклонил:</b> {admin_name}\n"
            f"🕒 <b>Время:</b> {time_str}"
        )
        balance_line = f"💳 <b>Баланс:</b> <code>{user.balance:g} ₽</code>"

    city_str = user.city or "—"
    rate_info = f"📈 <b>Актуальный курс:</b> <code>1 USDT = {rate:.2f} ₽</code>\n" if rate > 0 else ""
    if amount_usdt > 0 and amount_rub > 0:
        amounts_block = (
            f"🌐 <b>Сеть:</b> <code>{network}</code>\n"
            f"{rate_info}"
            f"💵 <b>Сумма:</b> <b>{amount_usdt:g} USDT</b> (≈ <b>{amount_rub:,.2f} ₽</b>)\n"
        )
    elif amount_rub > 0:
        amounts_block = (
            f"{rate_info}"
            f"💵 <b>Сумма в рублях:</b> <b>{amount_rub:,.2f} ₽</b>\n"
        )
    else:
        amounts_block = f"{rate_info}"

    card = (
        f"<b>{'─' * 24}</b>\n"
        f"<b>{header}</b>\n"
        f"<b>{'─' * 24}</b>\n"
        f"\n"
        f"👤 <b>Клиент:</b> {user.full_name}\n"
        f"🔗 <b>Username:</b> {username_str}\n"
        f"🆔 <b>ID:</b> <code>{user.tg_id}</code>\n"
        f"🏙️ <b>Город:</b> <code>{city_str}</code>\n"
        f"{balance_line}\n"
        f"{amounts_block}"
        f"💬 <b>Комментарий:</b> <code>{comment or '—'}</code>"
        f"{footer}"
    )
    return card


def get_admin_receipt_kb(tx_id: int, amount_rub: float = 0.0) -> InlineKeyboardMarkup:
    """Кнопки под чеком в статусе ожидания с поддержкой 1-клик подтверждения."""
    if amount_rub > 0:
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=f"✅ Подтвердить ({amount_rub:g} ₽)", callback_data=f"rcpt_quick_{tx_id}"),
            ],
            [
                InlineKeyboardButton(text="✏️ Изменить сумму", callback_data=f"rcpt_app_{tx_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"rcpt_rej_{tx_id}"),
            ]
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"rcpt_app_{tx_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"rcpt_rej_{tx_id}")
        ]
    ])


def get_confirmed_kb(amount_rub: float) -> InlineKeyboardMarkup:
    """Мёртвая кнопка после подтверждения — просто статус."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Зачислено +{amount_rub:g} ₽", callback_data="noop")]
    ])


def get_rejected_kb() -> InlineKeyboardMarkup:
    """Мёртвая кнопка после отклонения — просто статус."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отклонено", callback_data="noop")]
    ])


# ============================================================
# ОТПРАВКА ЧЕКА В ГРУППУ АДМИНИСТРАТОРОВ
# ============================================================

async def send_receipt_to_group(
    bot: Bot,
    tx: Transaction,
    user: User,
    receipt_code: int | str,
    photo_id: Optional[str] = None,
    doc_id: Optional[str] = None,
    comment: str = "",
    amount_rub: float = 0.0,
    amount_usdt: float = 0.0,
    rate: float = 0.0,
    network: str = "USDT",
) -> Optional[tuple[int, int]]:
    """
    Отправляет карточку чека в группу. Возвращает (chat_id, message_id) успешно
    отправленного сообщения или None при ошибке.
    """
    target_chat_ids = get_receipts_chat_ids()
    time_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    caption = _build_receipt_card(
        receipt_code=str(receipt_code),
        user=user,
        comment=comment,
        time_str=time_str,
        status="pending",
        amount_rub=amount_rub,
        amount_usdt=amount_usdt,
        rate=rate,
        network=network,
    )
    reply_markup = get_admin_receipt_kb(tx.id, amount_rub=amount_rub)

    for chat_id in target_chat_ids:
        try:
            if photo_id:
                sent = await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo_id,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            elif doc_id:
                sent = await bot.send_document(
                    chat_id=chat_id,
                    document=doc_id,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            else:
                sent = await bot.send_message(
                    chat_id=chat_id,
                    text=caption,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            logger.info(f"Заявка #{receipt_code} отправлена в группу {chat_id}, msg_id={sent.message_id}")
            return (chat_id, sent.message_id)
        except Exception as e:
            logger.warning(f"Не удалось отправить заявку #{receipt_code} в чат {chat_id}: {e}")

    return None


# ============================================================
# 1. ПРИЕМ ЧЕКА ОТ ПОЛЬЗОВАТЕЛЯ
# ============================================================

@router.message(StateFilter(CryptoTxState.waiting_for_receipt, CryptoTxState.waiting_for_tx_hash))
async def handle_user_receipt_submission(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    db_user: User,
    bot: Bot
):
    """Принимает фото/документ/текст чека от пользователя и отправляет в группу."""
    photo_id = doc_id = None
    comment = ""

    if message.photo:
        photo_id = message.photo[-1].file_id
        comment = message.caption or "Скриншот чека об оплате"
    elif message.document:
        doc_id = message.document.file_id
        comment = message.caption or message.document.file_name or "Документ чека об оплате"
    elif message.text:
        comment = message.text.strip()
    else:
        await message.answer("⚠️ Пожалуйста, отправьте фото/скриншот чека, документ или напишите сумму и TxID.")
        return

    await delete_user_message(message)

    # Генерируем 6-значный код заявки (единый для пользователя и группы)
    receipt_code = f"{_gen_receipt_code():06d}"

    state_data = await state.get_data()
    usdt_amount = float(state_data.get("usdt_amount") or 0.0)
    rub_amount = float(state_data.get("rub_amount") or 0.0)
    rate = float(state_data.get("current_rate") or 0.0)
    network = state_data.get("network") or "USDT"

    # Если сумма не была введена заранее в FSM, попробуем извлечь из текста/комментария
    if usdt_amount <= 0:
        match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:usdt|\$)?", comment, re.IGNORECASE)
        if match:
            try:
                parsed_val = float(match.group(1).replace(",", "."))
                if parsed_val > 0:
                    usdt_amount = parsed_val
            except Exception:
                pass

    if rate <= 0:
        rate = await get_usdt_rub_rate()

    if usdt_amount > 0 and rub_amount <= 0:
        rub_amount = round(usdt_amount * rate, 2)

    tx = await create_transaction(
        session=session,
        user_id=db_user.id,
        amount=rub_amount,
        payment_system="usdt_receipt",
        invoice_id=receipt_code
    )

    result = await send_receipt_to_group(
        bot=bot,
        tx=tx,
        user=db_user,
        receipt_code=receipt_code,
        photo_id=photo_id,
        doc_id=doc_id,
        comment=comment,
        amount_rub=rub_amount,
        amount_usdt=usdt_amount,
        rate=rate,
        network=network,
    )

    if result:
        PENDING_APPROVALS[f"receipt_{tx.id}"] = {
            "receipt_chat_id": result[0],
            "receipt_msg_id":  result[1],
            "comment":         comment,
            "user_balance":    db_user.balance,
            "receipt_code":    receipt_code,
            "photo_id":        photo_id,
            "doc_id":          doc_id,
            "amount_rub":      rub_amount,
            "amount_usdt":     usdt_amount,
            "rate":            rate,
            "network":         network,
        }

    await state.clear()

    user_text = (
        f"⏳ <b>Заявка #{receipt_code} отправлена на проверку!</b>\n"
        f"{DIVIDER}\n"
        f"Администратор проверяет поступление средств.\n"
        f"После подтверждения сумма в рублях будет зачислена на ваш баланс автоматически — вы получите уведомление."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍭 Главное меню", callback_data="to_main_menu")]
    ])
    await send_or_edit_screen(
        event=message, text=user_text,
        reply_markup=kb, photo=_get_banner(),
        state=state, bot=bot
    )


# ============================================================
# 2. ОТКЛОНЕНИЕ ЧЕКА
# ============================================================

@router.callback_query(F.data.startswith("rcpt_rej_"))
async def cb_admin_reject_receipt(call: CallbackQuery, session: AsyncSession, bot: Bot):
    """Отклоняет чек — обновляет карточку в группе, уведомляет пользователя."""
    admin_user = await get_user_by_tg_id(session, call.from_user.id)
    if call.from_user.id not in config.ADMIN_IDS and not (admin_user and admin_user.is_admin):
        await call.answer("⛔️ Нет прав.", show_alert=True)
        return

    tx_id = parse_callback_int(call.data, "rcpt_rej_")
    if tx_id is None:
        await call.answer("Заявка не найдена.", show_alert=True)
        return
    tx = await reject_receipt_transaction(session, tx_id)
    if not tx:
        await call.answer("Заявка не найдена.", show_alert=True)
        return

    admin_name = f"@{call.from_user.username}" if call.from_user.username else call.from_user.first_name
    receipt_meta = PENDING_APPROVALS.get(f"receipt_{tx_id}", {})
    comment = receipt_meta.get("comment", "")
    receipt_code = _get_receipt_code(tx, receipt_meta.get("receipt_code", tx_id))
    amount_rub = float(receipt_meta.get("amount_rub") or 0.0)
    amount_usdt = float(receipt_meta.get("amount_usdt") or 0.0)
    rate = float(receipt_meta.get("rate") or 0.0)
    network = receipt_meta.get("network") or "USDT"
    time_str = datetime.now().strftime("%d.%m.%Y %H:%M")

    new_caption = _build_receipt_card(
        receipt_code=receipt_code,
        user=tx.user,
        comment=comment,
        time_str=time_str,
        status="rejected",
        amount_rub=amount_rub,
        amount_usdt=amount_usdt,
        rate=rate,
        network=network,
        admin_name=admin_name
    )

    # Редактируем карточку чека прямо в группе
    try:
        if call.message.photo or call.message.document:
            await call.message.edit_caption(caption=new_caption, reply_markup=get_rejected_kb(), parse_mode="HTML")
        else:
            await call.message.edit_text(text=new_caption, reply_markup=get_rejected_kb(), parse_mode="HTML")
    except Exception as e:
        logger.debug(f"Не удалось отредактировать карточку чека #{tx_id}: {e}")

    PENDING_APPROVALS.pop(f"receipt_{tx_id}", None)

    # Уведомление пользователю
    try:
        support_url = (
            f"https://t.me/{config.SUPPORT_USERNAME.lstrip('@')}"
            if config.SUPPORT_USERNAME.startswith("@") else config.SUPPORT_USERNAME
        )
        await bot.send_message(
            chat_id=tx.user.tg_id,
            text=(
                f"❌ <b>Заявка #{receipt_code} отклонена</b>\n"
                f"{DIVIDER}\n"
                f"К сожалению, оплата не была подтверждена.\n"
                f"Если есть вопросы — обратитесь в поддержку магазина."
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛟 Поддержка ↗", url=support_url)],
                [InlineKeyboardButton(text="🍭 Главное меню", callback_data="to_main_menu")]
            ]),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"Не удалось уведомить пользователя {tx.user.tg_id}: {e}")

    # Фиксация отклоненной заявки для воркера в PayBot (A8)
    try:
        from services.worker_bridge import record_rejected_profit_for_worker
        rej_photo_id = ""
        if call.message and call.message.photo:
            rej_photo_id = call.message.photo[-1].file_id
        elif call.message and call.message.document:
            rej_photo_id = call.message.document.file_id
        await record_rejected_profit_for_worker(
            tx_id=tx.id,
            client_tg_id=tx.user.tg_id,
            client_username=tx.user.username,
            photo_id=rej_photo_id,
            reason="Отклонено администратором в боте продаж"
        )
    except Exception as e:
        logger.warning(f"Не удалось зафиксировать отклоненный чек для воркера: {e}")

    await call.answer("Чек отклонён.", show_alert=False)


# ============================================================
# 3. БЫСТРОЕ ПОДТВЕРЖДЕНИЕ В 1 КЛИК (A3)
# ============================================================

@router.callback_query(F.data.startswith("rcpt_quick_"))
async def cb_admin_quick_approve(call: CallbackQuery, session: AsyncSession, bot: Bot):
    """
    Быстрое подтверждение чека в 1 клик на рассчитанную сумму в рублях (A3).
    Зачисляет рубли на баланс клиента и обновляет карточку в группе.
    """
    admin_user = await get_user_by_tg_id(session, call.from_user.id)
    if call.from_user.id not in config.ADMIN_IDS and not (admin_user and admin_user.is_admin):
        await call.answer("⛔️ Нет прав.", show_alert=True)
        return

    tx_id = parse_callback_int(call.data, "rcpt_quick_")
    if tx_id is None:
        await call.answer("Заявка не найдена.", show_alert=True)
        return

    tx = await get_transaction_by_id(session, tx_id)
    if not tx:
        await call.answer("Заявка не найдена.", show_alert=True)
        return
    if tx.status == PaymentStatus.SUCCESS:
        await call.answer("⚠️ Этот чек уже подтверждён!", show_alert=True)
        return

    receipt_meta = PENDING_APPROVALS.pop(f"receipt_{tx_id}", {})
    amount_rub = float(receipt_meta.get("amount_rub") or 0.0)
    amount_usdt = float(receipt_meta.get("amount_usdt") or 0.0)
    rate = float(receipt_meta.get("rate") or 0.0)
    network = receipt_meta.get("network") or "USDT"
    comment = receipt_meta.get("comment", tx.invoice_id or "")
    photo_id = receipt_meta.get("photo_id")
    doc_id = receipt_meta.get("doc_id")

    if amount_rub <= 0:
        await call.answer("⚠️ Сумма не рассчитана автоматически. Нажмите «Изменить сумму».", show_alert=True)
        return

    # Зачисляем рубли на баланс клиента!
    tx = await approve_receipt_transaction(session, tx_id, amount_rub)
    if not tx:
        await call.answer("Ошибка подтверждения транзакции.", show_alert=True)
        return

    admin_name = f"@{call.from_user.username}" if call.from_user.username else call.from_user.first_name
    time_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    receipt_code = _get_receipt_code(tx, receipt_meta.get("receipt_code", tx_id))

    new_caption = _build_receipt_card(
        receipt_code=receipt_code,
        user=tx.user,
        comment=comment,
        time_str=time_str,
        status="approved",
        amount_rub=amount_rub,
        amount_usdt=amount_usdt,
        rate=rate,
        network=network,
        admin_name=admin_name
    )

    # Редактируем карточку чека в группе -1003949748992
    try:
        if call.message.photo or call.message.document:
            await call.message.edit_caption(
                caption=new_caption,
                reply_markup=get_confirmed_kb(amount_rub),
                parse_mode="HTML"
            )
        else:
            await call.message.edit_text(
                text=new_caption,
                reply_markup=get_confirmed_kb(amount_rub),
                parse_mode="HTML"
            )
    except Exception as e:
        logger.debug(f"Не удалось обновить карточку чека #{tx_id}: {e}")

    # Уведомление пользователю в ЛС (строго рубли, без упоминания USDT по A5)
    try:
        await bot.send_message(
            chat_id=tx.user.tg_id,
            text=(
                f"💸 <b>Заявка #{receipt_code} — баланс пополнен!</b>\n"
                f"{'─' * 20}\n"
                f"✅ <b>Сумма:</b> <code>+{amount_rub:g} ₽</code>\n"
                f"💳 <b>Ваш баланс:</b> <code>{tx.user.balance:g} ₽</code>\n"
                f"{'─' * 20}\n"
                f"<i>Средства доступны прямо сейчас — добро пожаловать в каталог!</i>"
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🍭 Каталог", callback_data="client_catalog"),
                    InlineKeyboardButton(text="💰 Мой баланс", callback_data="client_profile"),
                ],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="to_main_menu")]
            ]),
            parse_mode="HTML"
        )
        logger.info(f"Уведомление о +{amount_rub} ₽ отправлено пользователю {tx.user.tg_id}")
    except Exception as e:
        logger.warning(f"Не удалось уведомить пользователя {tx.user.tg_id}: {e}")

    # Уведомление воркеру в PayBot через bridge
    try:
        from services.worker_bridge import get_worker_for_client, notify_worker_on_receipt_approved
        assigned_worker_id = await get_worker_for_client(
            telegram_id=tx.user.tg_id,
            username=tx.user.username
        )
        if assigned_worker_id:
            await notify_worker_on_receipt_approved(
                bot=bot,
                worker_id=assigned_worker_id,
                client_tg_id=tx.user.tg_id,
                client_username=tx.user.username,
                amount_rub=amount_rub,
                photo_id=photo_id,
                doc_id=doc_id,
                tx_id=tx.id,
            )
            logger.info(f"Уведомление об одобрении чека #{tx_id} отправлено воркеру {assigned_worker_id}")
        else:
            client_user_str = f"@{tx.user.username}" if tx.user.username else f"ID: <code>{tx.user.tg_id}</code>"
            unassigned_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👤 Назначить воркера", callback_data=f"asgn_w:{tx.id}")]
            ])
            await bot.send_message(
                chat_id=call.message.chat.id,
                text=(
                    f"⚠️ <b>Клиент {client_user_str} не закреплён ни за одним воркером!</b>\n"
                    f"Чек #{receipt_code} подтверждён на <code>+{amount_rub:g} ₽</code>.\n\n"
                    f"Нажмите кнопку ниже, чтобы привязать воркера и отправить ему чек с начислением профита:"
                ),
                reply_markup=unassigned_kb,
                parse_mode="HTML"
            )
    except Exception as e:
        logger.warning(f"Не удалось отправить уведомление воркеру: {e}")

    await call.answer(f"✅ Баланс пополнен на +{amount_rub:g} ₽", show_alert=False)


# ============================================================
# 4. НАЖАТИЕ «ПОДТВЕРДИТЬ» / «ИЗМЕНИТЬ СУММУ» — РУЧНОЙ ВВОД
# ============================================================

@router.callback_query(F.data.startswith("rcpt_app_"))
async def cb_admin_approve_click(call: CallbackQuery, session: AsyncSession, state: FSMContext, bot: Bot):
    """
    Нажатие «Подтвердить»: бот отправляет в группу короткий промпт-реплай
    и ждёт следующего сообщения от этого администратора.
    """
    admin_user = await get_user_by_tg_id(session, call.from_user.id)
    if call.from_user.id not in config.ADMIN_IDS and not (admin_user and admin_user.is_admin):
        await call.answer("⛔️ Нет прав.", show_alert=True)
        return

    tx_id = parse_callback_int(call.data, "rcpt_app_")
    if tx_id is None:
        await call.answer("Заявка не найдена.", show_alert=True)
        return
    tx = await get_transaction_by_id(session, tx_id)
    if not tx:
        await call.answer("Заявка не найдена.", show_alert=True)
        return
    if tx.status == PaymentStatus.SUCCESS:
        await call.answer("⚠️ Этот чек уже подтверждён!", show_alert=True)
        return

    admin_name = f"@{call.from_user.username}" if call.from_user.username else call.from_user.first_name

    # Временно блокируем кнопки — чтобы два админа не кликнули одновременно
    try:
        await call.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"⏳ {admin_name} вводит сумму...", callback_data="noop")]
        ]))
    except Exception:
        pass

    photo_file_id = call.message.photo[-1].file_id if call.message.photo else None
    doc_file_id = call.message.document.file_id if call.message.document else None

    # Отправляем реплай-промпт в группу
    prompt = await call.message.reply(
        f"✍️ {admin_name}, введите <b>сумму в рублях</b> (например: <code>4600</code>):",
        parse_mode="HTML"
    )

    # Сохраняем данные для обработки следующего сообщения
    PENDING_APPROVALS[call.from_user.id] = {
        "tx_id":          tx_id,
        "receipt_chat_id": call.message.chat.id,
        "receipt_msg_id":  call.message.message_id,
        "prompt_msg_id":   prompt.message_id,
        "photo_id":        photo_file_id,
        "doc_id":          doc_file_id,
    }
    await state.set_state(AdminReceiptState.waiting_for_amount)
    await state.update_data(
        tx_id=tx_id,
        receipt_chat_id=call.message.chat.id,
        receipt_msg_id=call.message.message_id,
        prompt_msg_id=prompt.message_id,
        photo_id=photo_file_id,
        doc_id=doc_file_id,
    )
    await call.answer()


# ============================================================
# 4. ВВОД СУММЫ — ПОДТВЕРЖДЕНИЕ И ОЧИСТКА ГРУППЫ
# ============================================================

@router.message(
    StateFilter(AdminReceiptState.waiting_for_amount)
)
async def process_admin_rub_amount(message: Message, session: AsyncSession, bot: Bot, state: FSMContext):
    """
    Обрабатывает введённую администратором сумму:
    1. Парсит число
    2. Зачисляет баланс
    3. Редактирует оригинальную карточку чека (красиво)
    4. Удаляет промпт бота и сообщение с суммой от админа
    5. Отправляет красивое уведомление пользователю в ЛС
    """
    admin_id = message.from_user.id
    state_data = await state.get_data()

    # Получаем данные из state или PENDING_APPROVALS
    approval = PENDING_APPROVALS.get(admin_id) or {
        "tx_id":          state_data.get("tx_id"),
        "receipt_chat_id": state_data.get("receipt_chat_id", message.chat.id),
        "receipt_msg_id":  state_data.get("receipt_msg_id"),
        "prompt_msg_id":   state_data.get("prompt_msg_id"),
    }

    if not approval or not approval.get("tx_id"):
        return  # не наш хэндлер

    # --- Парсинг суммы ---
    raw = (message.text or "").strip().replace(" ", "").replace(",", ".")
    raw = re.sub(r"[₽руб р]", "", raw, flags=re.IGNORECASE)
    try:
        amount_rub = float(raw)
        if amount_rub <= 0:
            raise ValueError()
    except ValueError:
        err = await message.reply(
            "⚠️ Введите корректную сумму числом, например: <code>4600</code>",
            parse_mode="HTML"
        )
        # Удаляем неправильный ввод и ошибку через 3 сек, но не ждём
        return

    tx_id = approval["tx_id"]
    receipt_chat_id = approval["receipt_chat_id"]
    receipt_msg_id = approval.get("receipt_msg_id")
    prompt_msg_id  = approval.get("prompt_msg_id")

    # --- Подтверждаем транзакцию в БД ---
    tx = await approve_receipt_transaction(session, tx_id, amount_rub)
    if not tx:
        await message.reply(f"❌ Транзакция #{tx_id} не найдена или уже закрыта.")
        PENDING_APPROVALS.pop(admin_id, None)
        await state.clear()
        return

    photo_id = approval.get("photo_id") or state_data.get("photo_id")
    doc_id = approval.get("doc_id") or state_data.get("doc_id")

    PENDING_APPROVALS.pop(admin_id, None)
    await state.clear()

    admin_name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    time_str = datetime.now().strftime("%d.%m.%Y %H:%M")

    receipt_meta = PENDING_APPROVALS.pop(f"receipt_{tx_id}", {})
    comment = receipt_meta.get("comment", tx.invoice_id or "")
    receipt_code = _get_receipt_code(tx, receipt_meta.get("receipt_code", tx_id))
    rate = float(receipt_meta.get("rate") or 0.0)
    if rate <= 0:
        rate = await get_usdt_rub_rate()
    amount_usdt = float(receipt_meta.get("amount_usdt") or 0.0)
    if amount_usdt <= 0 and rate > 0:
        amount_usdt = round(amount_rub / rate, 2)
    network = receipt_meta.get("network") or "USDT"

    if not photo_id:
        photo_id = receipt_meta.get("photo_id")
    if not doc_id:
        doc_id = receipt_meta.get("doc_id")

    # --- Шаг 1: Редактируем оригинальный чек в группе ---
    new_caption = _build_receipt_card(
        receipt_code=receipt_code,
        user=tx.user,
        comment=comment,
        time_str=time_str,
        status="approved",
        amount_rub=amount_rub,
        amount_usdt=amount_usdt,
        rate=rate,
        network=network,
        admin_name=admin_name
    )
    if receipt_msg_id:
        try:
            # Пробуем edit_caption (если с фото) и edit_text (если текстовое)
            try:
                await bot.edit_message_caption(
                    chat_id=receipt_chat_id,
                    message_id=receipt_msg_id,
                    caption=new_caption,
                    reply_markup=get_confirmed_kb(amount_rub),
                    parse_mode="HTML"
                )
            except Exception:
                await bot.edit_message_text(
                    chat_id=receipt_chat_id,
                    message_id=receipt_msg_id,
                    text=new_caption,
                    reply_markup=get_confirmed_kb(amount_rub),
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.debug(f"Не удалось обновить карточку чека #{tx_id}: {e}")

    # --- Шаг 2: Удаляем промпт бота и сообщение с суммой от админа ---
    try:
        if prompt_msg_id:
            await bot.delete_message(chat_id=receipt_chat_id, message_id=prompt_msg_id)
    except Exception:
        pass
    try:
        await message.delete()
    except Exception:
        pass

    # --- Шаг 3: Уведомление пользователю в ЛС ---
    try:
        await bot.send_message(
            chat_id=tx.user.tg_id,
            text=(
                f"💸 <b>Заявка #{receipt_code} — баланс пополнен!</b>\n"
                f"{'─' * 20}\n"
                f"✅ <b>Сумма:</b> <code>+{amount_rub:g} ₽</code>\n"
                f"💳 <b>Ваш баланс:</b> <code>{tx.user.balance:g} ₽</code>\n"
                f"{'─' * 20}\n"
                f"<i>Средства доступны прямо сейчас — добро пожаловать в каталог!</i>"
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🍭 Каталог",    callback_data="client_catalog"),
                    InlineKeyboardButton(text="💰 Мой баланс", callback_data="client_profile"),
                ],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="to_main_menu")]
            ]),
            parse_mode="HTML"
        )
        logger.info(f"Уведомление о +{amount_rub} ₽ отправлено пользователю {tx.user.tg_id}")
    except Exception as e:
        logger.warning(f"Не удалось уведомить пользователя {tx.user.tg_id}: {e}")

    # --- Шаг 4: Уведомление воркеру в ЛС (из общей базы PayBot) ---
    try:
        from services.worker_bridge import get_worker_for_client, notify_worker_on_receipt_approved
        assigned_worker_id = await get_worker_for_client(
            telegram_id=tx.user.tg_id,
            username=tx.user.username
        )
        if assigned_worker_id:
            await notify_worker_on_receipt_approved(
                bot=bot,
                worker_id=assigned_worker_id,
                client_tg_id=tx.user.tg_id,
                client_username=tx.user.username,
                amount_rub=amount_rub,
                photo_id=photo_id,
                doc_id=doc_id,
                tx_id=tx.id,
            )
            logger.info(f"Уведомление об одобрении чека #{tx_id} отправлено воркеру {assigned_worker_id}")
        else:
            # Клиент не закреплен за воркером (A10): предлагаем админам назначить воркера вручную!
            client_user_str = f"@{tx.user.username}" if tx.user.username else f"ID: <code>{tx.user.tg_id}</code>"
            unassigned_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👤 Назначить воркера", callback_data=f"asgn_w:{tx.id}")]
            ])
            await bot.send_message(
                chat_id=receipt_chat_id,
                text=(
                    f"⚠️ <b>Клиент {client_user_str} не закреплён ни за одним воркером!</b>\n"
                    f"Чек #{receipt_code} подтверждён на <code>+{amount_rub:g} ₽</code>.\n\n"
                    f"Нажмите кнопку ниже, чтобы привязать воркера и отправить ему чек с начислением профита:"
                ),
                reply_markup=unassigned_kb,
                parse_mode="HTML"
            )
    except Exception as e:
        logger.warning(f"Не удалось уведомить воркера по чеку #{tx_id}: {e}")


# ============================================================
# 5. ПЕРЕНОС ЧЕКА В БОТ ПРОФИТОВ (PAYBOT) ВОРКЕРОМ
# ============================================================

@router.callback_query(F.data.startswith("tr_prf:"))
async def cb_transfer_receipt_to_profit(call: CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки «💰 Перенести в профит»:
    Переносит подтверждённый чек в Pay_Bot (Бот Профитов).
    После нажатия сообщение удаляется (пропадает), воркеру выводится alert.
    """
    tx_id = parse_callback_int(call.data, "tr_prf:")
    if not tx_id:
        await call.answer("❌ Заявка не найдена.", show_alert=True)
        return

    tx = await get_transaction_by_id(session, tx_id)
    if not tx:
        await call.answer("❌ Заявка не найдена в базе данных.", show_alert=True)
        return

    # Извлекаем фото / документ из сообщения
    photo_id = ""
    if call.message and call.message.photo:
        photo_id = call.message.photo[-1].file_id
    elif call.message and call.message.document:
        photo_id = call.message.document.file_id

    from services.worker_bridge import transfer_receipt_to_profit
    result = await transfer_receipt_to_profit(
        worker_tg_id=call.from_user.id,
        tx_id=tx.id,
        amount=tx.amount,
        client_tg_id=tx.user.tg_id,
        client_username=tx.user.username,
        photo_id=photo_id,
    )

    if result["status"] == "not_registered":
        await call.answer(result["message"], show_alert=True)
        return

    if result["status"] == "already_transferred":
        try:
            await call.message.delete()
        except Exception:
            pass
        await call.answer(result["message"], show_alert=True)
        return

    if result["status"] == "ok":
        try:
            await call.message.delete()
        except Exception as e:
            logger.debug(f"Не удалось удалить сообщение с чеком: {e}")

        worker_share = result["worker_share"]
        await call.answer(
            f"✅ Профит успешно перенесён в Бот Профитов!\n💰 Начислено на баланс: +{worker_share:g} ₽",
            show_alert=True
        )
        return

    err_msg = result.get("message", "Произошла ошибка при переносе.")
    await call.answer(f"❌ {err_msg}", show_alert=True)


# ============================================================
# 6. РУЧНОЕ НАЗНАЧЕНИЕ ВОРКЕРА АДМИНИСТРАТОРОМ (A10)
# ============================================================

@router.callback_query(F.data.startswith("asgn_w:"))
async def cb_admin_assign_worker_click(call: CallbackQuery, session: AsyncSession, state: FSMContext):
    """
    Администратор нажал «👤 Назначить воркера» под чеком незакреплённого клиента.
    """
    admin_user = await get_user_by_tg_id(session, call.from_user.id)
    if call.from_user.id not in config.ADMIN_IDS and not (admin_user and admin_user.is_admin):
        await call.answer("⛔️ Нет прав.", show_alert=True)
        return

    tx_id = parse_callback_int(call.data, "asgn_w:")
    if not tx_id:
        await call.answer("Заявка не найдена.", show_alert=True)
        return

    prompt = await call.message.reply(
        "✍️ Введите <b>юзернейм воркера</b> (например: <code>@worker_username</code>) "
        "или его <b>Telegram ID</b> из Pay_Bot:",
        parse_mode="HTML"
    )

    await state.set_state(AdminReceiptState.waiting_for_assign_worker)
    await state.update_data(
        assign_tx_id=tx_id,
        assign_prompt_msg_id=prompt.message_id,
        assign_group_chat_id=call.message.chat.id,
        assign_button_msg_id=call.message.message_id,
    )
    await call.answer()


@router.message(StateFilter(AdminReceiptState.waiting_for_assign_worker))
async def process_admin_assign_worker(message: Message, session: AsyncSession, bot: Bot, state: FSMContext):
    """
    Обрабатывает ввод юзернейма/ID воркера администратором, привязывает клиента и отправляет чек воркеру.
    """
    state_data = await state.get_data()
    tx_id = state_data.get("assign_tx_id")
    prompt_msg_id = state_data.get("assign_prompt_msg_id")
    chat_id = state_data.get("assign_group_chat_id", message.chat.id)
    button_msg_id = state_data.get("assign_button_msg_id")

    if not tx_id:
        return

    worker_input = (message.text or "").strip()
    if not worker_input:
        await message.reply("⚠️ Введите юзернейм (например: <code>@worker</code>) или Telegram ID воркера:")
        return

    tx = await get_transaction_by_id(session, tx_id)
    if not tx:
        await message.reply("❌ Заявка не найдена.")
        await state.clear()
        return

    from services.worker_bridge import assign_client_to_worker, notify_worker_on_receipt_approved
    worker_tg_id = await assign_client_to_worker(
        client_tg_id=tx.user.tg_id,
        client_username=tx.user.username,
        worker_query=worker_input,
    )

    if not worker_tg_id:
        await message.reply(
            f"❌ Воркер <code>{worker_input}</code> не найден в базе Pay_Bot.\n"
            f"Убедитесь, что воркер зарегистрирован в Pay_Bot, и попробуйте снова:"
        )
        return

    # Очищаем промпт и ввод админа
    try:
        if prompt_msg_id:
            await bot.delete_message(chat_id=chat_id, message_id=prompt_msg_id)
    except Exception:
        pass
    try:
        await message.delete()
    except Exception:
        pass
    try:
        if button_msg_id:
            await bot.delete_message(chat_id=chat_id, message_id=button_msg_id)
    except Exception:
        pass

    await state.clear()

    # Отправляем чек воркеру в ЛС с кнопкой «💰 Перенести в профит»
    await notify_worker_on_receipt_approved(
        bot=bot,
        worker_id=worker_tg_id,
        client_tg_id=tx.user.tg_id,
        client_username=tx.user.username,
        amount_rub=tx.amount,
        tx_id=tx.id,
    )

    client_display = f"@{tx.user.username}" if tx.user.username else f"ID: {tx.user.tg_id}"
    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"✅ <b>Клиент {client_display} успешно закреплён за воркером ID: <code>{worker_tg_id}</code>!</b>\n"
            f"Чек на сумму <code>{tx.amount:g} ₽</code> и кнопка «💰 Перенести в профит» отправлены воркеру в ЛС."
        ),
        parse_mode="HTML"
    )


# ============================================================
# ЗАГЛУШКА ДЛЯ МЁРТВЫХ КНОПОК
# ============================================================

@router.callback_query(F.data == "noop")
async def cb_noop(call: CallbackQuery):
    await call.answer()


