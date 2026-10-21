"""Worker: берёт задачи из jobs (FOR UPDATE SKIP LOCKED), ходит во внешние системы, пишет снапшоты и решения.
Запуск: python -m app.worker. Единственный процесс, который вызывает внешние ручки (docs/06 §1)."""

import asyncio
import logging

import httpx

from . import company, sources, store
from .domain import engine
from .policy import load as load_policy

log = logging.getLogger("worker")
RETRY_DELAYS_S = (2, 5, 15, 30, 60)        # дальше — FAILED, заявка уходит специалисту (docs/07 §8)
HANDLERS = {}


def handler(kind: str):
    def register(fn):
        HANDLERS[kind] = fn
        return fn
    return register


@handler("refresh_company")
async def refresh_company(conn, job: dict, client: httpx.AsyncClient) -> None:
    payload = job["payload"]
    result = await sources.refresh(conn, client, payload["inn"], with_bki=payload.get("with_bki", False))
    await store.add_event(conn, "registry.changed", "worker", {"inn": payload["inn"], "sources": result})


@handler("pipeline")
async def pipeline(conn, job: dict, client: httpx.AsyncClient) -> None:
    """Конвейер заявки: данные → решение → статус. Повторный запуск безопасен: решённую заявку не трогаем."""
    app = await store.get_application(conn, job["application_id"])
    if app["status"] == "SUBMITTED":
        app = await store.move(conn, app, "CHECKING", "worker", reason="старт конвейера")
    if app["status"] != "CHECKING":
        return
    inn = app["company_inn"]
    await store.add_event(conn, "step.changed", "worker", {"step": "sources", "state": "RUNNING"}, app["id"])
    fetched = await sources.refresh(conn, client, inn, with_bki=bool(app["data"].get("consent_bki")))
    await store.add_event(conn, "step.changed", "worker", {"step": "sources", "state": "DONE", "sources": fetched}, app["id"])

    facts, _ = await company.facts(conn, inn)
    decision = engine.decide(facts, app["data"]["request"], load_policy(), mode="commit")
    flags = list(dict.fromkeys(decision["flags"] + (["DEGRADED_DATA"] if facts["degraded"] else [])))
    async with conn.transaction():
        await store.add_event(conn, "decision.made", "engine", {
            "outcome": decision["outcome"], "offerKind": decision["offerKind"], "policyVersion": decision["policyVersion"],
            "reasons": decision["reasons"], "flags": flags}, app["id"])
        await store.move(conn, app, decision["status"], "engine", flags=flags, data_patch={"decision": decision},
                         reason=decision["outcome"])


async def run_once(pool, client: httpx.AsyncClient) -> bool:
    async with pool.acquire() as conn:
        if await store.kv_get(conn, "worker:paused", False):     # наш собственный сбой из песочницы (docs/07 §7)
            return False
        job = await store.claim(conn)
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


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    pool = await store.pool()
    log.info("worker started")
    async with httpx.AsyncClient(trust_env=False) as client:     # прокси из окружения не берём: внутренние вызовы
        while True:
            if not await run_once(pool, client):
                await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(main())
