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
    InlineKeyboardButton,
    FSInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from sqlalchemy.ext.asyncio import AsyncSession

from config import config, get_receipts_chat_ids
from database.models import User, PaymentStatus, Transaction
from database.crud import (
    create_transaction,
    get_transaction_by_id,
    approve_receipt_transaction,
    reject_receipt_transaction,
)
from states.client_states import CryptoTxState
from states.admin_states import AdminReceiptState
from utils.ui_cleaner import send_or_edit_screen, delete_user_message
from utils.formatters import DIVIDER

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
    admin_name: str = ""
) -> str:
    """Единственный источник разметки карточки чека — используется везде (группа + пользователь)."""
    username_str = f"@{user.username}" if user.username else "—"

    if status == "pending":
        header = f"🟡 ЗАЯВКА #{receipt_code} · ОЖИДАЕТ"
        footer = (
            f"\n\n<i>👆 Нажмите «Подтвердить» и введите сумму в рублях,\n"
            f"или «Отклонить» для возврата.</i>"
        )
        balance_line = f"💳 <b>Баланс до:</b> <code>{user.balance:g} ₽</code>"
    elif status == "approved":
        header = f"✅ ЗАЯВКА #{receipt_code} · ПОДТВЕРЖДЕНА"
        footer = (
            f"\n\n{'─' * 24}\n"
            f"✅ <b>Зачислено:</b> <code>+{amount_rub:g} ₽</code>\n"
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
        f"💬 <b>Комментарий:</b> <code>{comment or '—'}</code>"
        f"{footer}"
    )
    return card


def get_admin_receipt_kb(tx_id: int) -> InlineKeyboardMarkup:
    """Кнопки под чеком в статусе ожидания."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"rcpt_app_{tx_id}"),
            InlineKeyboardButton(text="❌ Отклонить",   callback_data=f"rcpt_rej_{tx_id}")
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
    receipt_code: int,
    photo_id: Optional[str] = None,
    doc_id: Optional[str] = None,
    comment: str = ""
) -> Optional[tuple[int, int]]:
    """
    Отправляет карточку чека в группу. Возвращает (chat_id, message_id) успешно
    отправленного сообщения или None при ошибке.
    """
    target_chat_ids = get_receipts_chat_ids()
    time_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    caption = _build_receipt_card(receipt_code, user, comment, time_str, status="pending")
    reply_markup = get_admin_receipt_kb(tx.id)

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

    tx = await create_transaction(
        session=session,
        user_id=db_user.id,
        amount=0.0,
        payment_system="usdt_receipt",
        invoice_id=receipt_code
    )

    result = await send_receipt_to_group(
        bot=bot, tx=tx, user=db_user, receipt_code=receipt_code,
        photo_id=photo_id, doc_id=doc_id, comment=comment
    )

    if result:
        PENDING_APPROVALS[f"receipt_{tx.id}"] = {
            "receipt_chat_id": result[0],
            "receipt_msg_id":  result[1],
            "comment":         comment,
            "user_balance":    db_user.balance,
            "receipt_code":    receipt_code,
        }

    await state.clear()

    user_text = (
        f"⏳ <b>Заявка #{receipt_code} отправлена на проверку!</b>\n"
        f"{DIVIDER}\n"
        f"Администратор проверяет поступление средств.\n"
        f"После подтверждения сумма в рублях будет зачислена на ваш баланс автоматически — вы получите уведомление."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌊 Главное меню", callback_data="to_main_menu")]
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
    if call.from_user.id not in config.ADMIN_IDS:
        await call.answer("⛔️ Нет прав.", show_alert=True)
        return

    tx_id = int(call.data.removeprefix("rcpt_rej_"))
    tx = await reject_receipt_transaction(session, tx_id)
    if not tx:
        await call.answer("Заявка не найдена.", show_alert=True)
        return

    admin_name = f"@{call.from_user.username}" if call.from_user.username else call.from_user.first_name
    receipt_meta = PENDING_APPROVALS.get(f"receipt_{tx_id}", {})
    comment = receipt_meta.get("comment", "")
    receipt_code = _get_receipt_code(tx, receipt_meta.get("receipt_code", tx_id))
    time_str = datetime.now().strftime("%d.%m.%Y %H:%M")

    new_caption = _build_receipt_card(
        receipt_code, tx.user, comment, time_str,
        status="rejected", admin_name=admin_name
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
                [InlineKeyboardButton(text="🌊 Главное меню", callback_data="to_main_menu")]
            ]),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"Не удалось уведомить пользователя {tx.user.tg_id}: {e}")

    await call.answer("Чек отклонён.", show_alert=False)


# ============================================================
# 3. НАЖАТИЕ «ПОДТВЕРДИТЬ» — ЗАПРОС СУММЫ
# ============================================================

@router.callback_query(F.data.startswith("rcpt_app_"))
async def cb_admin_approve_click(call: CallbackQuery, session: AsyncSession, state: FSMContext, bot: Bot):
    """
    Нажатие «Подтвердить»: бот отправляет в группу короткий промпт-реплай
    и ждёт следующего сообщения от этого администратора.
    """
    if call.from_user.id not in config.ADMIN_IDS:
        await call.answer("⛔️ Нет прав.", show_alert=True)
        return

    tx_id = int(call.data.removeprefix("rcpt_app_"))
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
    }
    await state.set_state(AdminReceiptState.waiting_for_amount)
    await state.update_data(
        tx_id=tx_id,
        receipt_chat_id=call.message.chat.id,
        receipt_msg_id=call.message.message_id,
        prompt_msg_id=prompt.message_id,
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

    PENDING_APPROVALS.pop(admin_id, None)
    await state.clear()

    admin_name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    time_str = datetime.now().strftime("%d.%m.%Y %H:%M")

    receipt_meta = PENDING_APPROVALS.pop(f"receipt_{tx_id}", {})
    comment = receipt_meta.get("comment", tx.invoice_id or "")
    receipt_code = _get_receipt_code(tx, receipt_meta.get("receipt_code", tx_id))

    # --- Шаг 1: Редактируем оригинальный чек в группе ---
    new_caption = _build_receipt_card(
        receipt_code, tx.user, comment, time_str,
        status="approved", amount_rub=amount_rub, admin_name=admin_name
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
                    InlineKeyboardButton(text="🌊 Каталог",    callback_data="client_catalog"),
                    InlineKeyboardButton(text="💰 Мой баланс", callback_data="client_profile"),
                ],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="to_main_menu")]
            ]),
            parse_mode="HTML"
        )
        logger.info(f"Уведомление о +{amount_rub} ₽ отправлено пользователю {tx.user.tg_id}")
    except Exception as e:
        logger.warning(f"Не удалось уведомить пользователя {tx.user.tg_id}: {e}")


# ============================================================
# ЗАГЛУШКА ДЛЯ МЁРТВЫХ КНОПОК
# ============================================================

@router.callback_query(F.data == "noop")
async def cb_noop(call: CallbackQuery):
    await call.answer()
