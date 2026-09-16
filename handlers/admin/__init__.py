from aiogram import Router
from filters.admin import IsAdmin
from .base import router as base_router
from .users_mgmt import router as users_mgmt_router
from .broadcast import router as broadcast_router
from .statistics import router as statistics_router
from .settings import router as settings_router
from .showcase_mgmt import router as showcase_router

admin_router = Router(name="admin_router")
# Защита всех админских маршрутов фильтром IsAdmin
admin_router.message.filter(IsAdmin())
admin_router.callback_query.filter(IsAdmin())

admin_router.include_router(base_router)
admin_router.include_router(users_mgmt_router)
admin_router.include_router(broadcast_router)
admin_router.include_router(statistics_router)
admin_router.include_router(settings_router)
admin_router.include_router(showcase_router)

__all__ = ["admin_router"]
