import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, update, BigInteger, String, Column, Float, Boolean, Text
from sqlalchemy.orm import declarative_base

logger = logging.getLogger(__name__)

# Путь к общей базе данных PayBot
DEFAULT_PAYBOT_DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "Pay_Bot", "paybot.db")
)
PAYBOT_DB_URL = os.getenv("PAYBOT_DB_URL", f"sqlite+aiosqlite:///{DEFAULT_PAYBOT_DB_PATH.replace(os.sep, '/')}")

engine = create_async_engine(PAYBOT_DB_URL, echo=False, future=True)
async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


class SharedClient(Base):
    __tablename__ = "clients"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, nullable=True, unique=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    worker_id = Column(BigInteger, nullable=False, index=True)


class SharedUser(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(64), nullable=True)
    first_name = Column(String(128), nullable=True)
    balance = Column(Float, default=0.0, nullable=False)
    is_authorized = Column(Boolean, default=False, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)


class SharedProfitRequest(Base):
    __tablename__ = "profit_requests"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    client_info = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    receipt_photo_id = Column(String(255), nullable=False)
    start_date = Column(String(20), nullable=False)
    pay_date = Column(String(20), nullable=False)
    worker_share = Column(Float, default=0.0, nullable=False)
    admin_share = Column(Float, default=0.0, nullable=False)
    status = Column(String(20), default="APPROVED", nullable=False)
    rejection_reason = Column(Text, nullable=True)
    admin_group_message_id = Column(BigInteger, nullable=True)


async def sync_client_on_start(username: Optional[str], telegram_id: int) -> Optional[int]:
    """
    При /start ищет клиента по username в таблице clients общей базы PayBot.
    Если находит — обновляет telegram_id клиента и возвращает worker_id.
    """
    if not username:
        return None

    clean_username = username.strip().lstrip("@").lower()
    try:
        async with async_session() as session:
            stmt = select(SharedClient).where(SharedClient.username == clean_username)
            res = await session.execute(stmt)
            client = res.scalar_one_or_none()

            if client:
                if client.telegram_id != telegram_id:
                    client.telegram_id = telegram_id
                    await session.commit()
                    logger.info("Client @%s assigned telegram_id=%s for worker=%s", clean_username, telegram_id, client.worker_id)
                return client.worker_id
    except Exception as e:
        logger.warning("Error syncing client in shared DB: %s", e)
    return None


async def get_worker_for_client(telegram_id: int, username: Optional[str] = None) -> Optional[int]:
    """
    Ищет воркера, за которым закреплен клиент (по telegram_id или username).
    """
    clean_username = username.strip().lstrip("@").lower() if username else None
    try:
        async with async_session() as session:
            stmt = select(SharedClient).where(
                (SharedClient.telegram_id == telegram_id) |
                ((SharedClient.username == clean_username) if clean_username else False)
            )
            res = await session.execute(stmt)
            client = res.scalar_one_or_none()
            if client:
                return client.worker_id
    except Exception as e:
        logger.warning("Error looking up worker for client: %s", e)
    return None


async def notify_worker_on_receipt_approved(
    bot: Bot,
    worker_id: int,
    client_tg_id: int,
    client_username: Optional[str],
    amount_rub: float,
    photo_id: Optional[str] = None,
    doc_id: Optional[str] = None,
    tx_id: Optional[int] = None,
) -> None:
    """
    Отправляет уведомление воркеру после подтверждения оплаты чека администратором в группе.
    Включает чек (фото/документ), сумму пополнения, ID клиента, юзернейм клиента
    и кнопку «💰 Перенести в профит».
    """
    client_tag = f"@{client_username.lstrip('@')}" if client_username else f"ID: <code>{client_tg_id}</code>"
    username_display = f"@{client_username.lstrip('@')}" if client_username else "не указан"

    text = (
        f"🎉 <b>Твой клиент {client_tag} скинул чек оплаты!</b>\n\n"
        f"Сохрани его и добавь профит в <b>Боте Профитов</b> через кнопку «💰 Добавить профит».\n\n"
        f"💵 <b>Сумма пополнения:</b> <code>{amount_rub:g} ₽</code>\n"
        f"🆔 <b>ID клиента:</b> <code>{client_tg_id}</code>\n"
        f"👤 <b>Юзернейм клиента:</b> {username_display}"
    )

    reply_markup = None
    if tx_id:
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Перенести в профит", callback_data=f"tr_prf:{tx_id}")]
        ])

    try:
        if photo_id:
            await bot.send_photo(
                chat_id=worker_id,
                photo=photo_id,
                caption=text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        elif doc_id:
            await bot.send_document(
                chat_id=worker_id,
                document=doc_id,
                caption=text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        else:
            await bot.send_message(
                chat_id=worker_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        logger.info(
            "Approved receipt notification sent to worker %s for client %s (amount: %s RUB, tx_id: %s)",
            worker_id, client_tag, amount_rub, tx_id
        )
    except TelegramForbiddenError:
        logger.warning("Worker %s blocked Sales Bot. Receipt not delivered to PM.", worker_id)
    except TelegramBadRequest as e:
        logger.error("Failed to send receipt notification to worker %s: %s", worker_id, e)
    except Exception as e:
        logger.error("Unexpected error sending receipt notification to worker %s: %s", worker_id, e)


async def transfer_receipt_to_profit(
    worker_tg_id: int,
    tx_id: int,
    amount: float,
    client_tg_id: int,
    client_username: Optional[str],
    photo_id: str,
) -> Dict[str, Any]:
    """
    Переносит подтверждённый чек в Pay_Bot:
    1. Проверяет регистрацию и авторизацию воркера в Pay_Bot.
    2. Проверяет защиту от повторного переноса (transfer_tx_{tx_id}).
    3. Создаёт ProfitRequest со статусом APPROVED.
    4. Начисляет долю воркеру (70%) на баланс в Pay_Bot.
    """
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    client_clean = f"@{client_username.lstrip('@')}" if client_username else f"ID: {client_tg_id}"
    transfer_tag = f"transfer_tx_{tx_id}"

    try:
        async with async_session() as session:
            # 1. Проверяем воркера в Pay_Bot
            stmt_user = select(SharedUser).where(SharedUser.telegram_id == worker_tg_id)
            res_user = await session.execute(stmt_user)
            worker = res_user.scalar_one_or_none()

            if not worker or not worker.is_authorized:
                return {
                    "status": "not_registered",
                    "message": "⚠️ Сначала запустите и зарегистрируйтесь в Боте Профитов!"
                }

            # 2. Защита от дублирования
            stmt_check = select(SharedProfitRequest).where(
                SharedProfitRequest.rejection_reason == transfer_tag
            )
            res_check = await session.execute(stmt_check)
            if res_check.scalar_one_or_none():
                return {
                    "status": "already_transferred",
                    "message": "⚠️ Этот чек уже был перенесён в профиты!"
                }

            # 3. Расчёт долей (70% воркер, 30% касса команды)
            worker_percent = float(os.getenv("WORKER_PERCENT", 70.0))
            admin_percent = float(os.getenv("ADMIN_PERCENT", 30.0))
            worker_share = round(amount * (worker_percent / 100.0), 2)
            admin_share = round(amount * (admin_percent / 100.0), 2)

            profit = SharedProfitRequest(
                user_id=worker.id,
                client_info=client_clean,
                amount=amount,
                receipt_photo_id=photo_id or "receipt_confirmed",
                start_date=now_str,
                pay_date=now_str,
                worker_share=worker_share,
                admin_share=admin_share,
                status="APPROVED",
                rejection_reason=transfer_tag,
            )
            session.add(profit)

            # 4. Начисляем баланс воркеру
            worker.balance = round(worker.balance + worker_share, 2)
            await session.commit()
            await session.refresh(profit)
            await session.refresh(worker)

            logger.info(
                "Profit #%s created and approved in PayBot for worker %s: +%s RUB (Total balance: %s RUB)",
                profit.id, worker_tg_id, worker_share, worker.balance
            )

            return {
                "status": "ok",
                "profit_id": profit.id,
                "worker_share": worker_share,
                "new_balance": worker.balance,
            }
    except Exception as e:
        logger.exception("Error transferring receipt to PayBot profit: %s", e)
        return {"status": "error", "message": f"Ошибка при переносе: {e}"}


async def forward_receipt_to_worker_and_admin(
    bot: Bot,
    photo_file_id: str,
    client_tg_id: int,
    client_username: Optional[str],
    worker_id: int,
    admin_group_id: Optional[int] = None,
) -> None:
    """
    Устаревшая функция пересылки (сохранена для обратной совместимости).
    """
    await notify_worker_on_receipt_approved(
        bot=bot,
        worker_id=worker_id,
        client_tg_id=client_tg_id,
        client_username=client_username,
        amount_rub=0.0,
        photo_id=photo_file_id,
    )
