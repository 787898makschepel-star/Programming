import os
import logging
from typing import Optional
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, update, BigInteger, String, Column, Float
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
) -> None:
    """
    Отправляет уведомление воркеру после подтверждения оплаты чека администратором в группе.
    Включает чек (фото/документ), сумму пополнения, ID клиента и юзернейм клиента.
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

    try:
        if photo_id:
            await bot.send_photo(
                chat_id=worker_id,
                photo=photo_id,
                caption=text,
                parse_mode="HTML",
            )
        elif doc_id:
            await bot.send_document(
                chat_id=worker_id,
                document=doc_id,
                caption=text,
                parse_mode="HTML",
            )
        else:
            await bot.send_message(
                chat_id=worker_id,
                text=text,
                parse_mode="HTML",
            )
        logger.info(
            "Approved receipt notification sent to worker %s for client %s (amount: %s RUB)",
            worker_id, client_tag, amount_rub
        )
    except TelegramForbiddenError:
        logger.warning("Worker %s blocked Sales Bot. Receipt not delivered to PM.", worker_id)
    except TelegramBadRequest as e:
        logger.error("Failed to send receipt notification to worker %s: %s", worker_id, e)
    except Exception as e:
        logger.error("Unexpected error sending receipt notification to worker %s: %s", worker_id, e)


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

