"""Песочница (docs/08): пресеты мира, отказы источников на лету, пауза воркера, «что если». Только при DEMO_MODE."""

import re
from decimal import Decimal
from pathlib import Path
from typing import Literal

import httpx
import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import store
from ..config import settings
from ..domain import engine
from ..jsonutil import plain
from ..policy import load as load_policy
from ..policy import sources as source_config

router = APIRouter(prefix="/sandbox", tags=["sandbox"])
PERSONAS = Path(__file__).resolve().parents[2] / "seed" / "personas.yaml"
ADMIN = f"{settings.wiremock_url}/__admin"


@router.get("/presets")
async def presets():
    """Компании демо-мира и их сценарии (seed/personas.yaml → моки WireMock)."""
    world = yaml.safe_load(PERSONAS.read_text("utf-8"))
    return {"today": world["today"], "items": [
        {"key": c["key"], "inn": c["inn"], "name": c["name"], "okved": c["okved"], "scenario": c.get("scenario")}
        for c in world["companies"]]}


class FaultIn(BaseModel):
    source: str = Field(description="ключ из policy/sources.yaml: egrul, bki, debtam…")
    mode: Literal["timeout", "error503", "reset", "garbage", "empty"]
    inn: str | None = Field(None, pattern=r"^\d{10}$|^\d{12}$", description="только для этой компании; пусто — для всех")


def fault_stub(source: str, mode: str, inn: str | None) -> dict:
    """Стаб отказа с приоритетом 1 поверх штатного (docs/07 §7)."""
    cfg = source_config()
    if source not in cfg["sources"]:
        raise HTTPException(422, f"неизвестный источник {source}")
    src = cfg["sources"][source]
    path, _, query = src["path"].partition("?")
    request: dict = {"method": src["method"]}
    if src["method"] == "POST":
        request["urlPath"] = path
        if inn:
            request["bodyPatterns"] = [{"matchesJsonPath": {"expression": "$.subject.inn", "equalTo": inn}}]
    elif query:                                             # ИНН в параметре запроса (ЕИС)
        request["urlPath"] = path
        param = query.split("=")[0]
        request["queryParameters"] = {param: {"equalTo": inn} if inn else {"matches": ".*"}}
    elif inn:
        request["urlPath"] = path.replace("{inn}", inn)
    else:
        request["urlPathPattern"] = re.escape(path).replace(re.escape("{inn}"), "[0-9]+")
    return {"priority": 1, "request": request, "response": cfg["faults"][mode],
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
