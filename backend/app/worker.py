"""Worker: берёт задачи из jobs (FOR UPDATE SKIP LOCKED), ходит во внешние системы, пишет снапшоты и решения;
между задачами — sweeper сроков по часам симулятора. Запуск: python -m app.worker.
Единственный процесс, который вызывает внешние ручки (docs/06 §1)."""

import asyncio
import logging
import time

import httpx

from . import lifecycle, sources, store
from .features import person_links

log = logging.getLogger("worker")
RETRY_DELAYS_S = (2, 5, 15, 30, 60)        # дальше — FAILED, заявка уходит специалисту (docs/07 §8)
SWEEP_EVERY_S = 1.0
DATA_JOBS = ("refresh_company", "refresh_person")   # на паузе стоят заявки, а данные компаний банк собирает дальше
HANDLERS = {}


def handler(kind: str):
    def register(fn):
        HANDLERS[kind] = fn
        return fn
    return register


async def _app(conn, job: dict) -> dict:
    return await lifecycle.load(conn, job["application_id"])


@handler("refresh_company")
async def refresh_company(conn, job: dict, client: httpx.AsyncClient) -> None:
    """Обновить снапшоты компании; если пришло событие мира — пересмотреть её оферты и подписи (RECHECK)."""
    payload = job["payload"]
    result = await sources.refresh(conn, client, payload["inn"], with_bki=payload.get("with_bki", False))
    await store.add_event(conn, "registry.changed", "worker", {"inn": payload["inn"], "sources": result})
    if payload.get("recheck"):
        await lifecycle.recheck(conn, payload["inn"], payload.get("reason"))


@handler("refresh_person")
async def refresh_person(conn, job: dict, client: httpx.AsyncClient) -> None:
    """Кто человек для банка: карточка клиента и компании с доступом в ДБО → обновить каждую компанию."""
    inn = job["payload"]["inn"]
    await sources.refresh(conn, client, inn, scope="person")
    card = (await store.snapshots(conn, inn)).get("bank_person")
    for link in person_links(card["payload"] if card else None):
        await sources.refresh(conn, client, link["inn"])


@handler("pipeline")
async def pipeline(conn, job: dict, client: httpx.AsyncClient) -> None:
    await lifecycle.start_checking(conn, await _app(conn, job))


@handler("decide")
async def decide(conn, job: dict, client: httpx.AsyncClient) -> None:
    await lifecycle.decide(conn, client, await _app(conn, job))


@handler("disburse")
async def disburse(conn, job: dict, client: httpx.AsyncClient) -> None:
    await lifecycle.disburse(conn, client, await _app(conn, job))


@handler("bki_followup")
async def bki_followup(conn, job: dict, client: httpx.AsyncClient) -> None:
    await lifecycle.bki_followup(conn, client, await _app(conn, job))


async def run_once(pool, client: httpx.AsyncClient) -> bool:
    async with pool.acquire() as conn:
        paused = await store.kv_get(conn, "worker:paused", False)    # наш собственный сбой из симулятора (docs/07 §7)
        job = await store.claim(conn, kinds=DATA_JOBS if paused else None)
    if job is None:
        return False
    async with pool.acquire() as conn:
        try:
            await HANDLERS[job["kind"]](conn, job, client)
            await store.finish(conn, job["id"], "DONE")
        except Exception as exc:  # noqa: BLE001 — любая ошибка шага уходит в ретрай, а не роняет воркер
            log.exception("job %s (%s) failed", job["id"], job["kind"])
            attempt = job["attempts"]
            if attempt > len(RETRY_DELAYS_S):
                await store.finish(conn, job["id"], "FAILED", repr(exc))
            else:
                await store.finish(conn, job["id"], "RETRY_WAIT", repr(exc), RETRY_DELAYS_S[attempt - 1])
    return True


async def sweep_once(pool) -> int:
    async with pool.acquire() as conn:
        if await store.kv_get(conn, "worker:paused", False):
            return 0
        return await lifecycle.sweep(conn)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    pool = await store.pool()
    log.info("worker started")
    last_sweep = 0.0
    async with httpx.AsyncClient(trust_env=False) as client:     # прокси из окружения не берём: внутренние вызовы
        while True:
            if time.monotonic() - last_sweep >= SWEEP_EVERY_S:
                try:
                    await sweep_once(pool)
                except Exception:  # noqa: BLE001 — сроки проверим на следующем круге
                    log.exception("sweep failed")
                last_sweep = time.monotonic()
            if not await run_once(pool, client):
                await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(main())
