"""Часы. В симуляторе — часы мира: при первом запуске стенда мир начинается с даты DEMO_TODAY (на неё построены моки),
дальше время идёт как обычно, а перемотка (`POST /sandbox/clock`, docs/08 §5) сдвигает его вперёд. Всё, что видит
пользователь, — по этим часам: «сегодня» кабинета и прогноза, создание и история заявки, сроки, выдача (база пишет свои
отметки тем же сдвигом — store.WORLD_NOW). В бою — обычное время без сдвига."""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from . import store
from .config import settings

OFFSET_KEY = store.CLOCK_OFFSET_KEY
ANCHOR_KEY = store.CLOCK_ANCHOR_KEY
TZ = ZoneInfo("Europe/Moscow")             # даты мира и кабинета — по Москве


async def offset(conn) -> int:
    """Перемотка вперёд, секунды."""
    return int(await store.kv_get(conn, OFFSET_KEY, 0)) if settings.demo_mode else 0


async def anchor(conn) -> float:
    """Мир минус реальное время, секунды. Фиксируется при первом обращении: мир стартует в DEMO_TODAY в текущее время
    суток по Москве — в какой бы день ни подняли стенд, даты мира совпадают с моками, а время дальше идёт как обычно."""
    if not settings.demo_mode:
        return 0.0
    value = await store.kv_get(conn, ANCHOR_KEY)
    if value is None:
        real = datetime.now(UTC)
        start = datetime.combine(date.fromisoformat(settings.demo_today), real.astimezone(TZ).timetz())
        value = await store.kv_setdefault(conn, ANCHOR_KEY, (start - real).total_seconds())
    return float(value)


async def shift(conn) -> timedelta:
    return timedelta(seconds=await anchor(conn) + await offset(conn))


async def now(conn) -> datetime:
    return datetime.now(UTC) + await shift(conn)


async def today(conn) -> date:
    return (await now(conn)).astimezone(TZ).date()


async def world(conn, real: datetime | None) -> datetime | None:
    """Отметка, которую база поставила по реальному времени (свежесть снапшота), → время мира."""
    return None if real is None else real + await shift(conn)
