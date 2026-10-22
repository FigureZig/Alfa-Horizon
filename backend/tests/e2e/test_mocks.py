"""Живой WireMock отвечает как мир: каждый источник по каждой компании и карточка каждого человека — то же тело,
что строит seed/world.py; чужой форме и незнакомому ИНН — 404 problem+json, поиск в ЕИС и реестре МЧД — пустой список.
Проверяется сервер с шаблонами ответов, а не файлы на диске (их сверяет tests/test_world.py)."""

import json
from datetime import date

import httpx
import pytest

from app.config import settings
from app.policy import sources as source_config
from app.sources import render
from seed import world

pytestmark = [pytest.mark.e2e, pytest.mark.anyio]

WORLD = world.load()
TODAY = date.fromisoformat(WORLD["today"])
SEARCH = {"eis": {"contracts": []}, "mchd": {"items": []}}   # поиск: ничего не нашлось — пустой список, а не 404
UNKNOWN = world.inn_ul("770100099") # ИНН с верной контрольной цифрой, которого нет в мире


async def _ask(client: httpx.AsyncClient, src: dict, inn: str) -> httpx.Response:
    url = settings.wiremock_url + render(src["path"], inn)
    if src["method"] == "POST":
        return await client.post(url, json=render(src.get("body", {}), inn))
    return await client.get(url)


def _absent(resp: httpx.Response, name: str) -> bool:
    if name in SEARCH:
        return resp.status_code == 200 and resp.json() == SEARCH[name]
    return resp.status_code == 404 and resp.headers["content-type"].startswith("application/problem+json")


async def test_every_source_answers_like_the_world(stand):
    sources = {k: v for k, v in source_config()["sources"].items() if v.get("scope") != "person"}
    assert world.inn_valid(UNKNOWN) and UNKNOWN not in {c["inn"] for c in WORLD["companies"]}
    async with httpx.AsyncClient(trust_env=False, timeout=10) as client:
        for company in WORLD["companies"]:
            served = world.served(company, WORLD["people"], TODAY)
            for name, src in sources.items():
                resp = await _ask(client, src, company["inn"])
                if name in served:
                    assert resp.status_code == 200 and resp.json() == served[name], (company["key"], name)
                else:
                    assert _absent(resp, name), (company["key"], name, resp.status_code)
        for name, src in sources.items():
            assert _absent(await _ask(client, src, UNKNOWN), name), name


async def test_bank_knows_every_person(stand):
    async with httpx.AsyncClient(trust_env=False, timeout=10) as client:
        for key, person in WORLD["people"].items():
            resp = await client.get(f"{settings.wiremock_url}/bank-core/v1/persons/{person['inn']}")
            card = json.loads(json.dumps(world.person_card(key, person, WORLD["companies"]), ensure_ascii=False, default=str))
            assert resp.status_code == 200 and resp.json() == card, key
