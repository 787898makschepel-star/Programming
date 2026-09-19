from aiogram.filters import Filter
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession
from database.crud import get_user_by_tg_id
from config import config


class IsAdmin(Filter):
    """
    Фильтр для проверки, является ли пользователь администратором бота.
    Сверяет user.id со списком ADMIN_IDS из файла конфигурации.
    """
    async def __call__(self, event: TelegramObject, session: AsyncSession) -> bool:
        user = getattr(event, "from_user", None)
        if not user:
            return False
        if user.id in config.ADMIN_IDS:
            return True
        db_user = await get_user_by_tg_id(session, user.id)
        return bool(db_user and db_user.is_admin)
