from sqlalchemy import text
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import config

# Если используется локальный SQLite, убедимся что папка для файла БД существует
if config.DB_URL.startswith("sqlite"):
    db_path = config.DB_URL.replace("sqlite+aiosqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

# Создание асинхронного движка SQLAlchemy
async_engine = create_async_engine(
    config.DB_URL,
    echo=False,
    future=True
)

# Фабрика сессий
async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    """Базовый класс для всех моделей SQLAlchemy 2.0"""
    pass


async def init_db():
    """
    Инициализация базы данных: создание всех таблиц, если они не существуют.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if conn.dialect.name == "sqlite":
            columns = await conn.execute(text("PRAGMA table_info(users)"))
            column_names = {row[1] for row in columns}
            if "district" not in column_names:
                await conn.execute(text("ALTER TABLE users ADD COLUMN district VARCHAR(64)"))
            if "referrer_id" not in column_names:
                await conn.execute(text("ALTER TABLE users ADD COLUMN referrer_id INTEGER"))
            if "referral_earnings" not in column_names:
                await conn.execute(text("ALTER TABLE users ADD COLUMN referral_earnings FLOAT NOT NULL DEFAULT 0"))
            showcase_columns = {
                row[1] for row in await conn.execute(text("PRAGMA table_info(showcase_products)"))
            }
            if showcase_columns and "category_id" not in showcase_columns:
                await conn.execute(text("ALTER TABLE showcase_products ADD COLUMN category_id INTEGER"))
            if showcase_columns and "unit" not in showcase_columns:
                await conn.execute(text("ALTER TABLE showcase_products ADD COLUMN unit VARCHAR(8) NOT NULL DEFAULT 'шт.'"))
            if showcase_columns and "start_quantity" not in showcase_columns:
                await conn.execute(text("ALTER TABLE showcase_products ADD COLUMN start_quantity FLOAT NOT NULL DEFAULT 1"))
        elif conn.dialect.name == "postgresql":
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS district VARCHAR(64)"))
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS referrer_id BIGINT"))
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_earnings DOUBLE PRECISION NOT NULL DEFAULT 0"))
            await conn.execute(text("ALTER TABLE showcase_products ADD COLUMN IF NOT EXISTS category_id BIGINT"))
            await conn.execute(text("ALTER TABLE showcase_products ADD COLUMN IF NOT EXISTS unit VARCHAR(8) NOT NULL DEFAULT 'шт.'"))
            await conn.execute(text("ALTER TABLE showcase_products ADD COLUMN IF NOT EXISTS start_quantity DOUBLE PRECISION NOT NULL DEFAULT 1"))


async def get_session() -> AsyncSession:
    """Генератор сессии для ручного вызова вне мидлварей."""
    async with async_session_factory() as session:
        yield session
