from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from config import config
from database.crud import get_or_create_user
from states.client_states import CaptchaState


class UserTrackerMiddleware(BaseMiddleware):
    """
    Мидлварь для автоматического сохранения/обновления пользователя в БД,
    блокировки доступа для заблокированных аккаунтов
    и строгой защиты от обхода капчи (капчу нельзя пропустить или надурить).
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

            # 1. Если пользователь заблокирован, прерываем обработку
            if db_user.is_banned:
                text = "⛔️ <b>Доступ ограничен.</b>\nВаш аккаунт был заблокирован администрацией магазина."
                if isinstance(event, Message):
                    await event.answer(text, parse_mode="HTML")
                elif isinstance(event, CallbackQuery):
                    await event.answer("⛔️ Вы заблокированы в этом боте.", show_alert=True)
                return None

            # 2. Проверка капчи (для всех пользователей, кроме администраторов)
            is_admin = (user.id in config.ADMIN_IDS) or bool(getattr(db_user, "is_admin", False))
            if not is_admin and not db_user.captcha_passed:
                # Ни один CallbackQuery (инлайн-кнопка) не сработает до прохождения капчи
                if isinstance(event, CallbackQuery):
                    await event.answer("🛡 Сначала решите капчу (проверочный пример) в чате с ботом!", show_alert=True)
                    return None

                # Сообщения в личных сообщениях с ботом
                if isinstance(event, Message) and event.chat.type == ChatType.PRIVATE:
                    msg_text = (event.text or "").strip()
                    # Разрешаем команду /start
                    if msg_text.startswith("/start"):
                        return await handler(event, data)

                    # Разрешаем ввод ответа на капчу, если пользователь находится в этом состоянии
                    state = data.get("state")
                    current_state = await state.get_state() if state else None
                    if current_state == CaptchaState.waiting_for_answer.state:
                        return await handler(event, data)

                    # Любые другие команды, текст или медиа блокируем до решения примера
                    await event.answer(
                        "🛡 <b>Доступ к боту ограничен.</b>\n\n"
                        "Пожалуйста, решите математический пример для входа.\n"
                        "Если пример не отображается, отправьте команду /start.",
                        parse_mode="HTML"
                    )
                    return None

        return await handler(event, data)
