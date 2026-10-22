"""Часы. В симуляторе — дата мира (DEMO_TODAY, моки построены на неё) плюс сдвиг часов: сроки оферты, подписи
и дозапроса видно без ожидания (docs/08 §5, `time.advance`). В бою сдвига нет."""

from datetime import UTC, date, datetime, timedelta

from . import store
from .config import settings

OFFSET_KEY = "sandbox:clock_offset_s"


async def offset(conn) -> int:
    return int(await store.kv_get(conn, OFFSET_KEY, 0)) if settings.demo_mode else 0


async def now(conn) -> datetime:
    return datetime.now(UTC) + timedelta(seconds=await offset(conn))


async def today(conn) -> date:
    base = date.fromisoformat(settings.demo_today) if settings.demo_mode else datetime.now(UTC).date()
    return base + timedelta(seconds=await offset(conn))
