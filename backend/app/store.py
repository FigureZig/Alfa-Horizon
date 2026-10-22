"""PostgreSQL: 5 таблиц (docs/06 §4) на asyncpg без ORM. Заявка, её события и задачи пишутся в одной транзакции (outbox)."""

import hashlib
import json
import uuid

import asyncpg

from .config import settings
from .domain import state
from .jsonutil import canonical, dumps, plain

_pool: asyncpg.Pool | None = None


async def _init_conn(conn: asyncpg.Connection) -> None:
    for kind in ("json", "jsonb"):
        await conn.set_type_codec(kind, encoder=dumps, decoder=json.loads, schema="pg_catalog")


async def pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=10, init=_init_conn)
    return _pool


async def listener() -> asyncpg.Connection:
    """Отдельное соединение для LISTEN (живой таймлайн заявки): занято всё время потока, поэтому не из пула."""
    conn = await asyncpg.connect(settings.database_url)
    await _init_conn(conn)
    return conn


async def close() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


# ── снапшоты ─────────────────────────────────────────────────────────────────────────────────────────────────────


async def put_snapshot(conn, source: str, key: str, status: str, payload=None, error: str | None = None) -> None:
    digest = hashlib.sha256(dumps(payload).encode()).hexdigest() if payload is not None else None
    if status == "error":   # источник упал — последний удачный ответ не затираем (stale-while-revalidate, docs/06 §3)
        await conn.execute(
            """INSERT INTO snapshots (source, key, status, error) VALUES ($1, $2, 'error', $3)
               ON CONFLICT (source, key) DO UPDATE SET error = $3,
                 status = CASE WHEN snapshots.payload IS NULL THEN 'error' ELSE snapshots.status END""",
            source, key, error)
        return
    await conn.execute(
        """INSERT INTO snapshots (source, key, payload, status, error, fetched_at, hash) VALUES ($1, $2, $3, $4, NULL, now(), $5)
           ON CONFLICT (source, key) DO UPDATE SET payload = $3, status = $4, error = NULL, fetched_at = now(), hash = $5""",
        source, key, payload, status, digest)


async def snapshots(conn, key: str) -> dict[str, dict]:
    rows = await conn.fetch("SELECT source, payload, status, error, fetched_at FROM snapshots WHERE key = $1", key)
    return {r["source"]: dict(r) for r in rows}


# ── kv ───────────────────────────────────────────────────────────────────────────────────────────────────────────


async def kv_get(conn, key: str, default=None):
    value = await conn.fetchval("SELECT value FROM kv WHERE key = $1", key)
    return default if value is None else value


async def kv_set(conn, key: str, value) -> None:
    await conn.execute("""INSERT INTO kv (key, value, updated_at) VALUES ($1, $2, now())
                          ON CONFLICT (key) DO UPDATE SET value = $2, updated_at = now()""", key, value)


async def kv_delete(conn, key: str) -> None:
    await conn.execute("DELETE FROM kv WHERE key = $1", key)


# ── события (аудит с хэш-цепочкой) ───────────────────────────────────────────────────────────────────────────────


def _link(prev: str | None, type_: str, application_id, body) -> str:
    """Звено цепочки аудита: хэш предыдущей записи + тип + заявка + канонический JSON события (docs/10 P19)."""
    return hashlib.sha256(f"{prev}|{type_}|{application_id}|{canonical(body)}".encode()).hexdigest()


async def verify_chain(conn) -> dict:
    """Пересчитать цепочку аудита: любая правка или удаление записи ломает звено, и видно, с какой записи."""
    prev, count = None, 0
    for row in await conn.fetch("SELECT id, application_id, type, payload, prev_hash, hash FROM events ORDER BY id"):
        count += 1
        if row["prev_hash"] != prev or row["hash"] != _link(prev, row["type"], row["application_id"], row["payload"]):
            return {"events": count, "intact": False, "broken_at": row["id"], "last_hash": prev}
        prev = row["hash"]
    return {"events": count, "intact": True, "broken_at": None, "last_hash": prev}


async def add_event(conn, type_: str, actor: str, payload: dict, application_id=None, idempotency_key=None) -> None:
    await conn.execute("SELECT pg_advisory_xact_lock(4242)")       # одна цепочка без развилок
    prev = await conn.fetchval("SELECT hash FROM events ORDER BY id DESC LIMIT 1")
    body = plain(payload)
    digest = _link(prev, type_, application_id, body)
    await conn.execute(
        """INSERT INTO events (application_id, type, actor, payload, idempotency_key, prev_hash, hash)
           VALUES ($1, $2, $3, $4, $5, $6, $7) ON CONFLICT (idempotency_key) DO NOTHING""",
        application_id, type_, actor, body, idempotency_key, prev, digest)


async def events(conn, application_id) -> list[dict]:
    rows = await conn.fetch("SELECT id, at, type, actor, payload FROM events WHERE application_id = $1 ORDER BY id",
                            application_id)
    return [dict(r) for r in rows]


# ── задачи (очередь на SKIP LOCKED, docs/06 §6) ────────────────────────────────────────────────────────────────────


async def enqueue(conn, kind: str, payload: dict | None = None, application_id=None, delay_s: float = 0) -> None:
    await conn.execute("""INSERT INTO jobs (kind, application_id, payload, run_at)
                          VALUES ($1, $2, $3, now() + make_interval(secs => $4))""",
                       kind, application_id, payload or {}, delay_s)


async def pending(conn, kind: str, application_id) -> bool:
    return bool(await conn.fetchval("""SELECT 1 FROM jobs WHERE kind = $1 AND application_id = $2
                                       AND status IN ('PENDING', 'RUNNING', 'RETRY_WAIT') LIMIT 1""", kind, application_id))


async def claim(conn, lease_s: int = 120) -> dict | None:
    row = await conn.fetchrow(
        """UPDATE jobs SET status = 'RUNNING', attempts = attempts + 1, lease_until = now() + make_interval(secs => $1)
           WHERE id = (SELECT id FROM jobs
                       WHERE (status IN ('PENDING', 'RETRY_WAIT') AND run_at <= now())
                          OR (status = 'RUNNING' AND lease_until < now())       -- воркер упал: перезапуск
                       ORDER BY run_at FOR UPDATE SKIP LOCKED LIMIT 1)
           RETURNING *""", lease_s)
    return dict(row) if row else None


async def finish(conn, job_id: int, status: str = "DONE", error: str | None = None, retry_in_s: float = 0) -> None:
    await conn.execute("""UPDATE jobs SET status = $2, last_error = $3, lease_until = NULL,
                                         run_at = now() + make_interval(secs => $4) WHERE id = $1""",
                       job_id, status, error, retry_in_s)


# ── заявки ───────────────────────────────────────────────────────────────────────────────────────────────────────


async def create_application(conn, company_inn: str, data: dict, actor: str) -> dict:
    app_id = uuid.uuid4()
    async with conn.transaction():
        row = await conn.fetchrow("""INSERT INTO applications (id, company_inn, status, data)
                                     VALUES ($1, $2, 'DRAFT', $3) RETURNING *""", app_id, company_inn, plain(data))
        await add_event(conn, "application.status_changed", actor, {"from": None, "to": "DRAFT"}, app_id)
    return dict(row)


async def get_application(conn, app_id) -> dict | None:
    row = await conn.fetchrow("SELECT * FROM applications WHERE id = $1", app_id)
    return dict(row) if row else None


async def move(conn, app: dict, to: str, actor: str, *, flags=None, data_patch: dict | None = None,
               reason: str | None = None, idempotency_key: str | None = None) -> dict:
    """Переход статуса с проверкой по таблице и оптимистической блокировкой; событие в той же транзакции."""
    state.check(app["status"], to)
    data = {**app["data"], **plain(data_patch or {})}
    async with conn.transaction():
        row = await conn.fetchrow(
            """UPDATE applications SET status = $3, flags = $4, data = $5, version = version + 1, updated_at = now()
               WHERE id = $1 AND version = $2 RETURNING *""",
            app["id"], app["version"], to, list(flags if flags is not None else app["flags"]), data)
        if row is None:
            raise state.TransitionError("заявку изменили параллельно — повторите действие")
        await add_event(conn, "application.status_changed", actor,
                        {"from": app["status"], "to": to, "reason": reason}, app["id"], idempotency_key)
    return dict(row)


async def patch(conn, app: dict, actor: str, event: str, payload: dict, *, flags=None, data_patch: dict | None = None,
                idempotency_key: str | None = None) -> dict:
    """Изменение без смены статуса (подпись добавлена, флаг SLA): та же блокировка и событие в той же транзакции."""
    data = {**app["data"], **plain(data_patch or {})}
    async with conn.transaction():
        row = await conn.fetchrow(
            """UPDATE applications SET flags = $3, data = $4, version = version + 1, updated_at = now()
               WHERE id = $1 AND version = $2 RETURNING *""",
            app["id"], app["version"], list(flags if flags is not None else app["flags"]), data)
        if row is None:
            raise state.TransitionError("заявку изменили параллельно — повторите действие")
        await add_event(conn, event, actor, payload, app["id"], idempotency_key)
    return dict(row)


async def queue(conn, statuses=("UNDER_REVIEW",)) -> list[dict]:
    rows = await conn.fetch("SELECT * FROM applications WHERE status = ANY($1) ORDER BY updated_at", list(statuses))
    return [dict(r) for r in rows]


async def applications(conn, company_inn: str) -> list[dict]:
    rows = await conn.fetch("SELECT * FROM applications WHERE company_inn = $1 ORDER BY created_at DESC", company_inn)
    return [dict(r) for r in rows]


async def with_deadlines(conn) -> list[dict]:
    """Заявки, у которых тикает срок: сроки статусов и SLA ручного рассмотрения (sweeper worker)."""
    rows = await conn.fetch("""SELECT * FROM applications
                               WHERE data ? 'deadline' AND data->'deadline' <> 'null'::jsonb OR status = 'UNDER_REVIEW'""")
    return [dict(r) for r in rows]
