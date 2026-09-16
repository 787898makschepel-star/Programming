from aiogram.filters import Filter
from aiogram.types import TelegramObject
from config import config


class IsAdmin(Filter):
    """
    Фильтр для проверки, является ли пользователь администратором бота.
    Сверяет user.id со списком ADMIN_IDS из файла конфигурации.
    """
    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        if not user:
            return False
        return user.id in config.ADMIN_IDS
