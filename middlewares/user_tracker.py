from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from database.crud import get_or_create_user


class UserTrackerMiddleware(BaseMiddleware):
    """
    Мидлварь для автоматического сохранения/обновления пользователя в БД
    и блокировки доступа для заблокированных аккаунтов.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, data)

        session: AsyncSession = data.get("session")
        if session:
            db_user, created = await get_or_create_user(
                session=session,
                tg_id=user.id,
                username=user.username,
                full_name=user.full_name or ""
            )
            data["db_user"] = db_user

            # Если пользователь заблокирован, прерываем обработку
            if db_user.is_banned:
                text = "⛔️ <b>Доступ ограничен.</b>\nВаш аккаунт был заблокирован администрацией магазина."
                if isinstance(event, Message):
                    await event.answer(text, parse_mode="HTML")
                elif isinstance(event, CallbackQuery):
                    await event.answer("⛔️ Вы заблокированы в этом боте.", show_alert=True)
                return None

        return await handler(event, data)
