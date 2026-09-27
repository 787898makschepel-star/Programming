import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database.connection import async_session_factory, async_engine, init_db
from middlewares.db_session import DbSessionMiddleware
from middlewares.user_tracker import UserTrackerMiddleware
from handlers import main_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    """Действия при запуске бота."""
    logger.info("Инициализация базы данных...")
    await init_db()
    async with async_session_factory() as session:
        from database.seed_data import seed_initial_catalog
        await seed_initial_catalog(session)
        from database.seed_data import seed_showcase_catalog
        await seed_showcase_catalog(session)
    logger.info("База данных успешно инициализирована и наполнена товарами.")

    # Оповещение администраторов
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text="🚀 <b>Бот-магазин успешно запущен и готов к работе!</b>\n"
                     "Для входа в панель управления введите команду /admin",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление админу {admin_id}: {e}")


async def on_shutdown(bot: Bot):
    """Корректное завершение работы сервисов при остановке."""
    logger.info("Остановка бота и закрытие сессии...")
    await bot.session.close()


async def main():
    """Точка входа в приложение."""
    tokens = [token for token in (config.BOT_TOKEN, config.BOT_TOKEN_2) if token]
    if not tokens:
        raise ValueError("Не задан BOT_TOKEN или BOT_TOKEN_2")

    bots = [Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML)) for token in tokens]
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(DbSessionMiddleware(session_factory=async_session_factory))
    dp.message.middleware(UserTrackerMiddleware())
    dp.callback_query.middleware(UserTrackerMiddleware())
    dp.include_router(main_router)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        for bot in bots:
            await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Запуск long-polling для %s ботов...", len(bots))
        await dp.start_polling(*bots, allowed_updates=dp.resolve_used_update_types())
    finally:
        for bot in bots:
            await bot.session.close()
        await async_engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот принудительно остановлен.")
