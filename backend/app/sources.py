"""Один http-клиент на все внешние источники (docs/07 §3): таймауты, ретраи с полным jitter, breaker, снапшоты.

Настройки и пути — policy/sources.yaml; моки — WireMock (backend/wiremock). Вызывает только worker.
"""

import asyncio
import random
import time

import httpx

from . import store
from .config import settings
from .policy import sources as source_config


class SourceUnavailable(Exception):
    pass


def applies(src: dict, inn: str) -> bool:
    kind = src.get("kind", "ALL")
    return kind == "ALL" or (kind == "UL") == (len(inn) == 10)


def render(obj, inn: str):
    if isinstance(obj, str):
        return obj.replace("{inn}", inn)
    if isinstance(obj, dict):
        return {k: render(v, inn) for k, v in obj.items()}
    if isinstance(obj, list):
        return [render(v, inn) for v in obj]
    return obj


async def call(client: httpx.AsyncClient, name: str, inn: str) -> tuple[str, dict | list | None]:
    """→ ("ok", payload) | ("not_found", None); исчерпаны ретраи → SourceUnavailable."""
    cfg = source_config()
    src = cfg["sources"][name]
    opt = {**cfg["defaults"], **src}
    url = settings.wiremock_url + render(src["path"], inn)
    timeout = httpx.Timeout(opt["timeout_s"], connect=opt["connect_timeout_s"])
    last_error = "нет ответа"
    for attempt in range(1, opt["attempts"] + 1):
        try:
            if src["method"] == "POST":
                resp = await client.post(url, json=render(src.get("body", {}), inn), timeout=timeout)
            else:
                resp = await client.get(url, timeout=timeout)
            if resp.status_code == 404:
                return "not_found", None
            if resp.status_code < 400:
                return "ok", resp.json()           # битый JSON → ValueError → ретрай
            if resp.status_code < 500 and resp.status_code != 429:
                raise SourceUnavailable(f"{name}: HTTP {resp.status_code}")   # ошибка запроса — не ретраим
            last_error = f"HTTP {resp.status_code}"
        except (httpx.TransportError, ValueError) as exc:   # таймаут, обрыв, мусор в ответе
            last_error = type(exc).__name__
        if attempt < opt["attempts"]:
            await asyncio.sleep(random.uniform(0, min(opt["backoff_cap_s"], opt["backoff_base_s"] * 2 ** attempt)))
    raise SourceUnavailable(f"{name}: {last_error}")


def in_scope(src: dict, scope: str) -> bool:
    return src.get("scope", "company") == scope


async def refresh(conn, client: httpx.AsyncClient, inn: str, *, with_bki: bool = False, scope: str = "company",
                  only: tuple[str, ...] = ()) -> dict[str, str]:
    """Обновить снапшоты по всем подходящим источникам (или только по only). БКИ — только при согласии (218-ФЗ ст. 6 ч. 9)."""
    cfg = source_config()
    names = [n for n, s in cfg["sources"].items() if in_scope(s, scope) and applies(s, inn)
             and (with_bki or not s.get("needs_consent")) and (not only or n in only)]
    breaker = cfg["defaults"]["breaker"]
    states = {n: await store.kv_get(conn, f"breaker:{n}", {"failures": 0, "open_until": 0}) for n in names}
    now = time.time()
    to_call = [n for n in names if states[n]["open_until"] <= now]
    results = await asyncio.gather(*(call(client, n, inn) for n in to_call), return_exceptions=True)

    outcome = {n: "breaker_open" for n in names if n not in to_call}
    for name in outcome:
        await store.put_snapshot(conn, name, inn, "error", error="breaker open")
    for name, res in zip(to_call, results, strict=True):
        st = states[name]
        if isinstance(res, Exception):
            st["failures"] += 1
            if st["failures"] >= breaker["failures"]:
                st["open_until"] = now + breaker["open_s"]
            await store.put_snapshot(conn, name, inn, "error", error=str(res))
            outcome[name] = "error"
        else:
            st.update(failures=0, open_until=0)
            status, payload = res
            await store.put_snapshot(conn, name, inn, status, payload)
            outcome[name] = status
        await store.kv_set(conn, f"breaker:{name}", st)
    return outcome
