"""Песочница (docs/08): пресеты мира, своя персона, отказы источников на лету, пауза воркера, «что если».
Только при DEMO_MODE."""

import re
from datetime import date
from decimal import Decimal
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from seed import world

from .. import store
from ..config import settings, today
from ..domain import engine
from ..jsonutil import plain
from ..policy import load as load_policy
from ..policy import sources as source_config

router = APIRouter(prefix="/sandbox", tags=["sandbox"])
ADMIN = f"{settings.wiremock_url}/__admin"
JSON_HEADERS = {"Content-Type": "application/json; charset=utf-8"}
PERSONA_BASE = 9000                      # номера своих персон: ИНН 7705…/7706…/7707… не пересекаются с демо-миром


@router.get("/presets")
async def presets():
    """Компании демо-мира и их сценарии (seed/personas.yaml → моки WireMock)."""
    data = world.load()
    return {"today": data["today"], "items": [
        {"key": c["key"], "inn": c["inn"], "name": c["name"], "okved": c["okved"], "scenario": c.get("scenario")}
        for c in data["companies"]]}


class PersonaIn(BaseModel):
    """Своя персона: компания из нескольких параметров. ИНН, ОГРН, люди, выписка и ответы всех источников
    строятся тем же seed/world.py, что и демо-мир, и проходят ту же проверку корректности."""
    kind: Literal["IP", "LLC", "JSC"] = "LLC"
    okved: str = Field("62.01", pattern=r"^\d{2}(\.\d{1,2}){0,2}$", description="ОКВЭД 2: от него отрасль, продукты, спред")
    okved_name: str = "Основной вид деятельности"
    age_months: int = Field(36, ge=1, le=600, description="сколько месяцев бизнесу")
    headcount: int = Field(12, ge=1, le=250)
    inflow_avg: int = Field(3_000_000, ge=10_000, description="средние поступления на счёт в месяц, ₽")
    inflow_cv: float = Field(0.3, ge=0, le=1, description="разброс поступлений от месяца к месяцу")
    inflow_trend: float = Field(0.0, ge=-0.9, le=1, description="последние 3 месяца к предыдущим 9, минус 1")
    debt_load: float = Field(0.15, ge=0, le=1, description="платежи по текущим кредитам / поступления")
    overdue_days: int = Field(0, ge=0, le=365, description="максимальная просрочка в КИ")
    bki_requests: int = Field(1, ge=0, le=50, description="запросы в БКИ за 30 дней")
    tax_debt: int = Field(0, ge=0, description="недоимка, ₽")
    participants: int = Field(1, ge=1, le=10, description="участников ООО")
    profit_margin: float = Field(0.05, ge=-1, le=1, description="чистая прибыль / выручка")
    flags: list[Literal["liquidation", "bankruptcy", "unreliable_eio", "disqualified_eio"]] = []
    contract_price: int | None = Field(None, gt=0, description="действующий госконтракт в ЕИС, ₽")


def match(src: dict, inn: str | None) -> dict:
    """Как WireMock узнаёт запрос worker к источнику (пути — policy/sources.yaml); inn=None — любой ИНН."""
    path, _, query = src["path"].partition("?")
    request: dict = {"method": src["method"]}
    if src["method"] == "POST":
        request["urlPath"] = path
        if inn:
            request["bodyPatterns"] = [{"matchesJsonPath": {"expression": "$.subject.inn", "equalTo": inn}}]
    elif query:                                             # ИНН в параметре запроса (ЕИС)
        request["urlPath"] = path
        request["queryParameters"] = {query.split("=")[0]: {"equalTo": inn} if inn else {"matches": ".*"}}
    elif inn:
        request["urlPath"] = path.replace("{inn}", inn)
    else:
        request["urlPathPattern"] = re.escape(path).replace(re.escape("{inn}"), "[0-9]+")
    return request


def persona_stubs(company: dict, people: dict, on: date) -> list[dict]:
    """Стабы с приоритетом 3: выше штатных (5) и «не найдено» (9), ниже отказов песочницы (1)."""
    cfg, inn = source_config(), company["inn"]
    meta = {"createdBy": "sandbox-persona", "inn": inn, "name": company["name"]}

    def stub(request: dict, body, source: str) -> dict:
        return {"priority": 3, "request": request, "response": {"status": 200, "headers": JSON_HEADERS, "jsonBody": body},
                "metadata": {**meta, "source": source}}

    stubs = [stub(match(cfg["sources"][s], inn), body, s) for s, body in world.served(company, people, on).items()]
    stubs += [stub({"method": "GET", "urlPath": f"/bank-core/v1/persons/{p['inn']}"}, world.person_card(key, p), "bank_person")
              for key, p in people.items()]
    if world.is_ul(company):
        stubs.append(stub({"method": "GET", "urlPath": "/girbo/v1/organizations/search",
                           "queryParameters": {"query": {"equalTo": inn}}}, world.girbo_search(company), "girbo_search"))
    return stubs


@router.post("/personas", status_code=201)
async def create_persona(body: PersonaIn):
    """Собрать свою персону и поставить её ответы в WireMock на лету; worker сразу подтягивает данные компании."""
    spec = {**body.model_dump(exclude={"okved", "okved_name"}), "okved": [body.okved, body.okved_name]}
    pool = await store.pool()
    async with pool.acquire() as conn:
        seq = await store.kv_get(conn, "sandbox:persona_seq", 0) + 1
        await store.kv_set(conn, "sandbox:persona_seq", seq)
    company, people = world.custom(spec, PERSONA_BASE + seq % 1000, today())
    errors = world.validate(company, people, today())
    if errors:
        raise HTTPException(422, {"errors": errors})
    stubs = persona_stubs(company, people, today())
    async with httpx.AsyncClient(trust_env=False) as client:
        resp = await client.post(f"{ADMIN}/mappings/import", json={
            "mappings": stubs, "importOptions": {"duplicatePolicy": "OVERWRITE", "deleteAllNotInImport": False}})
        resp.raise_for_status()
    async with pool.acquire() as conn:
        await store.enqueue(conn, "refresh_company", {"inn": company["inn"]})
    return {"inn": company["inn"], "name": company["name"], "ogrn": company["ogrn"], "stubs": len(stubs),
            "people": [{"inn": people[p]["inn"], "fio": " ".join(people[p]["fio"]), "level": level}
                       for p, level in company["access"]]}


@router.get("/personas")
async def list_personas():
    async with httpx.AsyncClient(trust_env=False) as client:
        resp = await client.post(f"{ADMIN}/mappings/find-by-metadata",
                                 json={"matchesJsonPath": {"expression": "$.createdBy", "equalTo": "sandbox-persona"}})
        resp.raise_for_status()
    found: dict[str, dict] = {}
    for m in resp.json().get("mappings", []):
        item = found.setdefault(m["metadata"]["inn"], {"inn": m["metadata"]["inn"], "name": m["metadata"]["name"], "stubs": 0})
        item["stubs"] += 1
    return {"items": list(found.values())}


class FaultIn(BaseModel):
    source: str = Field(description="ключ из policy/sources.yaml: egrul, bki, debtam…")
    mode: Literal["timeout", "error503", "reset", "garbage", "empty"]
    inn: str | None = Field(None, pattern=r"^\d{10}$|^\d{12}$", description="только для этой компании; пусто — для всех")


def fault_stub(source: str, mode: str, inn: str | None) -> dict:
    """Стаб отказа с приоритетом 1 поверх штатного (docs/07 §7)."""
    cfg = source_config()
    if source not in cfg["sources"]:
        raise HTTPException(422, f"неизвестный источник {source}")
    return {"priority": 1, "request": match(cfg["sources"][source], inn), "response": cfg["faults"][mode],
            "metadata": {"createdBy": "sandbox", "source": source, "mode": mode, "inn": inn}}


@router.post("/faults", status_code=201)
async def add_fault(body: FaultIn):
    async with httpx.AsyncClient(trust_env=False) as client:
        resp = await client.post(f"{ADMIN}/mappings", json=fault_stub(body.source, body.mode, body.inn))
        resp.raise_for_status()
    return {"id": resp.json()["id"], **body.model_dump()}


@router.get("/faults")
async def list_faults():
    async with httpx.AsyncClient(trust_env=False) as client:
        resp = await client.post(f"{ADMIN}/mappings/find-by-metadata",
                                 json={"matchesJsonPath": {"expression": "$.createdBy", "equalTo": "sandbox"}})
        resp.raise_for_status()
    return {"items": [{"id": m["id"], **m["metadata"]} for m in resp.json().get("mappings", [])]}


@router.delete("/faults/{fault_id}", status_code=204)
async def remove_fault(fault_id: str):
    async with httpx.AsyncClient(trust_env=False) as client:
        await client.delete(f"{ADMIN}/mappings/{fault_id}")


@router.post("/reset")
async def reset():
    """Вернуть штатный мир: снять все отказы и сбросить сценарии WireMock, снять паузу воркера."""
    async with httpx.AsyncClient(trust_env=False) as client:
        await client.post(f"{ADMIN}/mappings/reset")
        await client.post(f"{ADMIN}/scenarios/reset")
    pool = await store.pool()
    async with pool.acquire() as conn:
        await store.kv_set(conn, "worker:paused", False)
    return {"status": "ok"}


@router.post("/worker/{action}")
async def worker(action: Literal["pause", "resume"]):
    """Наш собственный сбой: воркер перестаёт брать задачи, API продолжает работать."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        await store.kv_set(conn, "worker:paused", action == "pause")
    return {"paused": action == "pause"}


class WhatIfIn(BaseModel):
    facts: dict = Field(description="факты в формате features.company_facts")
    request: dict = Field(description="{product, amount, term_months, goal, corporate_approval, collateral_value}")
    mode: Literal["simulate", "commit"] = "simulate"


@router.post("/decision")
async def what_if(body: WhatIfIn):
    """Движок на произвольных фактах — для отладки правил и демонстрации «что если»."""
    facts = {k: Decimal(str(v)) if k in {"tax_debt", "inflow_avg", "debt_payments", "assets", "revenue", "net_profit"}
             and v is not None else v for k, v in body.facts.items()}
    return plain(engine.decide(facts, body.request, load_policy(), body.mode))
