from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
import os
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import config

CITY_RESET_MIGRATION_ID = "2026_09_reset_user_cities"


def normalize_async_database_url(database_url: str) -> URL:
    """Use the asyncpg driver for Render's standard PostgreSQL connection URL."""
    url = make_url(database_url)
    if url.drivername in {"postgres", "postgresql"}:
        return url.set(drivername="postgresql+asyncpg")
    return url

# Если используется локальный SQLite, убедимся что папка для файла БД существует
if config.DB_URL.startswith("sqlite"):
    db_path = config.DB_URL.replace("sqlite+aiosqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

# Создание асинхронного движка SQLAlchemy
async_engine = create_async_engine(
    normalize_async_database_url(config.DB_URL),
    echo=False,
    future=True
)

from sqlalchemy import event

@event.listens_for(async_engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Швейцарские часы: WAL-режим, синхронизация NORMAL, таймаут 60с и внешние ключи."""
    if config.DB_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.execute("PRAGMA busy_timeout = 60000")
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

# Фабрика сессий
async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)



class Base(DeclarativeBase):
    """Базовый класс для всех моделей SQLAlchemy 2.0"""
    pass


async def _apply_city_reset_migration(conn: AsyncConnection) -> None:
    await conn.execute(text(
        "CREATE TABLE IF NOT EXISTS bot_migrations ("
        "migration_id VARCHAR(128) PRIMARY KEY)"
    ))
    migration = await conn.execute(
        text(
            "INSERT INTO bot_migrations (migration_id) VALUES (:migration_id) "
            "ON CONFLICT (migration_id) DO NOTHING"
        ),
        {"migration_id": CITY_RESET_MIGRATION_ID},
    )
    if migration.rowcount:
        await conn.execute(text("UPDATE users SET city = '', district = NULL"))


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
            if "is_admin" not in column_names:
                await conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"))
            if "start_count" not in column_names:
                await conn.execute(text("ALTER TABLE users ADD COLUMN start_count INTEGER NOT NULL DEFAULT 0"))
            if "start_pending" not in column_names:
                await conn.execute(text("ALTER TABLE users ADD COLUMN start_pending BOOLEAN NOT NULL DEFAULT 0"))
            if "captcha_passed" not in column_names:
                await conn.execute(text("ALTER TABLE users ADD COLUMN captcha_passed BOOLEAN NOT NULL DEFAULT 0"))
            showcase_columns = {
                row[1] for row in await conn.execute(text("PRAGMA table_info(showcase_products)"))
            }
            if showcase_columns and "category_id" not in showcase_columns:
                await conn.execute(text("ALTER TABLE showcase_products ADD COLUMN category_id INTEGER"))
            if showcase_columns and "unit" not in showcase_columns:
                await conn.execute(text("ALTER TABLE showcase_products ADD COLUMN unit VARCHAR(8) NOT NULL DEFAULT 'шт.'"))
            if showcase_columns and "start_quantity" not in showcase_columns:
                await conn.execute(text("ALTER TABLE showcase_products ADD COLUMN start_quantity FLOAT NOT NULL DEFAULT 1"))
            await conn.execute(text("UPDATE showcase_products SET start_quantity = 3 WHERE unit LIKE 'шт%' AND (start_quantity IS NULL OR start_quantity < 3)"))
            await conn.execute(text("UPDATE showcase_products SET start_quantity = 0.5 WHERE (unit LIKE 'г%' OR unit = 'g') AND (start_quantity IS NULL OR start_quantity < 0.5)"))
        elif conn.dialect.name == "postgresql":
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS district VARCHAR(64)"))
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS referrer_id BIGINT"))
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_earnings DOUBLE PRECISION NOT NULL DEFAULT 0"))
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE"))
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS start_count INTEGER NOT NULL DEFAULT 0"))
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS start_pending BOOLEAN NOT NULL DEFAULT FALSE"))
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS captcha_passed BOOLEAN NOT NULL DEFAULT FALSE"))
            await conn.execute(text("ALTER TABLE showcase_products ADD COLUMN IF NOT EXISTS category_id BIGINT"))
            await conn.execute(text("ALTER TABLE showcase_products ADD COLUMN IF NOT EXISTS unit VARCHAR(8) NOT NULL DEFAULT 'шт.'"))
            await conn.execute(text("ALTER TABLE showcase_products ADD COLUMN IF NOT EXISTS start_quantity DOUBLE PRECISION NOT NULL DEFAULT 1"))
            await conn.execute(text("UPDATE showcase_products SET start_quantity = 3 WHERE unit LIKE 'шт%' AND (start_quantity IS NULL OR start_quantity < 3)"))
            await conn.execute(text("UPDATE showcase_products SET start_quantity = 0.5 WHERE (unit LIKE 'г%' OR unit = 'g') AND (start_quantity IS NULL OR start_quantity < 0.5)"))

        await _apply_city_reset_migration(conn)


async def get_session() -> AsyncSession:
    """Генератор сессии для ручного вызова вне мидлварей."""
    async with async_session_factory() as session:
        yield session
