"""Применяет SQL-миграции из migrations/ по порядку, каждую один раз. Запуск: python -m app.migrate"""

import asyncio
from pathlib import Path

import asyncpg

from .config import settings

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"


async def main() -> None:
    conn = await asyncpg.connect(settings.database_url)
    try:
        await conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations "
                           "(version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())")
        done = {r["version"] for r in await conn.fetch("SELECT version FROM schema_migrations")}
        for path in sorted(MIGRATIONS.glob("*.sql")):
            if path.name in done:
                continue
            async with conn.transaction():
                await conn.execute(path.read_text("utf-8"))
                await conn.execute("INSERT INTO schema_migrations (version) VALUES ($1)", path.name)
            print(f"migration applied: {path.name}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
