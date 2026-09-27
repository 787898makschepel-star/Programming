import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from database.connection import _apply_city_reset_migration


def test_city_reset_migration_runs_only_once():
    async def run_migration_test():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        try:
            async with engine.begin() as conn:
                await conn.execute(text(
                    "CREATE TABLE users ("
                    "id INTEGER PRIMARY KEY, city VARCHAR(64) NOT NULL, district VARCHAR(64))"
                ))
                await conn.execute(text(
                    "INSERT INTO users (id, city, district) VALUES "
                    "(1, 'Москва', 'Центральный'), (2, 'Казань', 'Советский')"
                ))

                await _apply_city_reset_migration(conn)
                cleared_users = (await conn.execute(
                    text("SELECT city, district FROM users ORDER BY id")
                )).all()
                assert cleared_users == [("", None), ("", None)]

                await conn.execute(text(
                    "UPDATE users SET city = 'Пермь', district = 'Ленинский' WHERE id = 1"
                ))
                await _apply_city_reset_migration(conn)
                saved_city = (await conn.execute(
                    text("SELECT city, district FROM users WHERE id = 1")
                )).one()
                assert saved_city == ("Пермь", "Ленинский")
        finally:
            await engine.dispose()

    asyncio.run(run_migration_test())