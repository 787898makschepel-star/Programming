from aiogram import Router
from .start import router as start_router
from .catalog import router as catalog_router
from .profile import router as profile_router

client_router = Router(name="client_router")
client_router.include_router(start_router)
client_router.include_router(catalog_router)
client_router.include_router(profile_router)

__all__ = ["client_router"]
