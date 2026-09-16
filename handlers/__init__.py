from aiogram import Router
from .client import client_router
from .admin import admin_router
from .payments import router as payments_router
from .receipts import router as receipts_router

main_router = Router(name="main_router")
main_router.include_router(admin_router)
main_router.include_router(client_router)
main_router.include_router(payments_router)
main_router.include_router(receipts_router)

__all__ = ["main_router"]
