import asyncio
from typing import List, Dict, Any, Optional
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError, TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup


class BroadcastService:
    """
    Сервис массовой рассылки сообщений с контролем лимитов Telegram
    и защитой от блокировок.
    """

    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_to_user(
        self,
        user_id: int,
        text: str,
        photo_id: Optional[str] = None,
        reply_markup: Optional[InlineKeyboardMarkup] = None
    ) -> str:
        """
        Отправка сообщения одному пользователю.
        Возвращает: 'success', 'blocked', 'error'.
        """
        try:
            if photo_id:
                await self.bot.send_photo(
                    chat_id=user_id,
                    photo=photo_id,
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            else:
                await self.bot.send_message(
                    chat_id=user_id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            return "success"
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            return await self.send_to_user(user_id, text, photo_id, reply_markup)
        except TelegramForbiddenError:
            # Пользователь заблокировал бота
            return "blocked"
        except (TelegramBadRequest, Exception):
            return "error"

    async def run_broadcast(
        self,
        user_ids: List[int],
        text: str,
        photo_id: Optional[str] = None,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        delay: float = 0.05
    ) -> Dict[str, int]:
        """
        Пакетная отправка сообщений всем пользователям из списка.
        """
        stats = {
            "total": len(user_ids),
            "success": 0,
            "blocked": 0,
            "errors": 0
        }

        for uid in user_ids:
            res = await self.send_to_user(uid, text, photo_id, reply_markup)
            if res == "success":
                stats["success"] += 1
            elif res == "blocked":
                stats["blocked"] += 1
            else:
                stats["errors"] += 1

            if delay > 0:
                await asyncio.sleep(delay)

        return stats
