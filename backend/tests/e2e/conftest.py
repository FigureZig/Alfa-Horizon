"""Сквозные сценарии на живых Postgres и WireMock: API работает в процессе теста (httpx.ASGITransport),
worker выполняется по одной задаче — так видно каждый переход и можно вмешаться между шагами.

Запуск: Postgres и WireMock на портах из docker-compose.yml (55432 и 8081), затем `uv run pytest -m e2e`.
Рабочую базу тесты не трогают: у них своя E2E_DATABASE_URL (по умолчанию credit_e2e), её они создают и чистят сами.
Нет Postgres или WireMock — тесты пропускаются.
"""

import os
import re
from pathlib import Path

import asyncpg
import httpx
import pytest
from pydantic import ValidationError

from app import config, store, worker
from app.api import schemas
from app.main import app

E2E_DB = os.getenv("E2E_DATABASE_URL", "postgresql://app:app@localhost:55432/credit_e2e")
MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def pool(anyio_backend):
    server, name = E2E_DB.rsplit("/", 1)
    try:
        admin = await asyncpg.connect(f"{server}/postgres", timeout=3)
    except (OSError, asyncpg.PostgresError) as exc:
        pytest.skip(f"нет Postgres для e2e ({exc})")
    if not await admin.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", name):
        await admin.execute(f'CREATE DATABASE "{name}"')
    await admin.close()
    async with httpx.AsyncClient(trust_env=False) as client:
        try:
            (await client.get(f"{config.settings.wiremock_url}/__admin/mappings", timeout=3)).raise_for_status()
        except httpx.HTTPError as exc:
            pytest.skip(f"нет WireMock для e2e ({exc})")
    conn = await asyncpg.connect(E2E_DB)
    await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    for path in sorted(MIGRATIONS.glob("*.sql")):
        await conn.execute(path.read_text("utf-8"))
    await conn.close()
    object.__setattr__(config.settings, "database_url", E2E_DB)      # settings заморожены — подменяем только в тестах
    await store.close()
    yield await store.pool()
    await store.close()


class Stand:
    """API, worker и песочница одного теста."""

    def __init__(self, api: httpx.AsyncClient, pool, outside: httpx.AsyncClient):
        self.api, self.pool, self.outside = api, pool, outside

    async def call(self, method: str, path: str, headers: dict | None = None, *, expect: int | None = None, **kw):
        resp = await self.api.request(method, path, headers=headers, **kw)
        if expect is not None:
            assert resp.status_code == expect, (method, path, resp.status_code, resp.text)
        elif resp.status_code >= 400:
            raise AssertionError(f"{method} {path} → {resp.status_code}: {resp.text}")
        return resp.json().get("data") if resp.content else None

    async def step(self, *, fast_forward: bool = False) -> bool:
        """Одна задача worker. fast_forward — отложенные задачи считаем наступившими (ждать в тесте незачем)."""
        if fast_forward:
            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE jobs SET run_at = now() WHERE status IN ('PENDING', 'RETRY_WAIT')")
        return await worker.run_once(self.pool, self.outside)

    async def pump(self, limit: int = 100) -> None:
        for _ in range(limit):
            if not await self.step():
                return
        raise AssertionError("worker не успокоился за 100 задач")

    async def login(self, persona_id: str) -> dict:
        data = await self.call("POST", f"/sandbox/personas/{persona_id}/login", params={"wait_s": 0})
        await self.pump()
        return {"Authorization": f"Bearer {data['token']}"}

    async def status(self, app_id: str) -> str:
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT status FROM applications WHERE id = $1", app_id)

    async def path(self, app_id: str) -> list[str]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""SELECT payload->>'to' AS status FROM events
                                       WHERE application_id = $1 AND type = 'application.status_changed' ORDER BY id""", app_id)
        return [r["status"] for r in rows]

    async def until_left(self, app_id: str, status: str, *, fast_forward: bool = False, limit: int = 30) -> None:
        for _ in range(limit):
            if await self.status(app_id) != status:
                return
            if not await self.step(fast_forward=fast_forward):
                raise AssertionError(f"задач больше нет, а заявка всё ещё {status}")
        raise AssertionError(f"заявка застряла в {status}")

    async def advance(self, seconds: int) -> None:
        await self.call("POST", "/sandbox/clock", json={"advance_s": seconds})
        await worker.sweep_once(self.pool)


ROUTES = [(re.compile("^" + re.sub(r"\{[^}]+\}", "[^/]+", path) + "$"), ops) for path, ops in app.openapi()["paths"].items()]


def documented(method: str, path: str, status: int):
    """Модель успешного ответа из контракта OpenAPI ($ref → app/api/schemas.py) — или None, если ручка не найдена."""
    for pattern, ops in ROUTES:
        if pattern.match(path) and method.lower() in ops:
            response = ops[method.lower()]["responses"].get(str(status), {})
            ref = response.get("content", {}).get("application/json", {}).get("schema", {}).get("$ref", "")
            return getattr(schemas, ref.rsplit("/", 1)[-1], None) if ref else None
    return None


@pytest.fixture
async def stand(pool):
    """Каждый успешный JSON-ответ сверяется со схемой своей ручки: документация не расходится с API."""
    mismatches = []

    async def check(response: httpx.Response) -> None:
        if response.status_code >= 300 or not response.headers.get("content-type", "").startswith("application/json"):
            return
        await response.aread()
        model = documented(response.request.method, response.request.url.path, response.status_code)
        if model is None:
            return
        try:
            model.model_validate(response.json())
        except ValidationError as exc:
            mismatches.append(f"{response.request.method} {response.request.url.path}: {exc}")

    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE events, jobs, applications, snapshots, kv RESTART IDENTITY CASCADE")
    async with (httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://e2e/api/v1",
                                  event_hooks={"response": [check]}) as api,
                httpx.AsyncClient(trust_env=False) as outside):
        stand = Stand(api, pool, outside)
        await stand.call("POST", "/sandbox/reset")
        yield stand
    assert not mismatches, "ответы не совпадают с OpenAPI:\n" + "\n".join(mismatches[:5])
