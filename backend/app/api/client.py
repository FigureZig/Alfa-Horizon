"""Клиентский путь: каталог и калькулятор, что банк знает о компании, подбор, заявка."""

from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Path, Query
from pydantic import BaseModel, Field

from .. import company, store
from ..domain import calc, catalog, engine
from ..jsonutil import plain
from ..policy import load as load_policy

router = APIRouter()
Inn = Annotated[str, Path(pattern=r"^\d{10}$|^\d{12}$", description="ИНН: 10 цифр — юрлицо, 12 — ИП")]
Product = Literal["OVERDRAFT", "EXPRESS", "WORKING_CAPITAL", "INVESTMENT", "CONTRACT", "AGRO_SEASONAL"]
Goal = Literal["cash_gap", "stock", "equipment", "growth", "contract"]


@router.get("/health/live", tags=["system"])
async def live():
    return {"status": "ok"}


@router.get("/health/ready", tags=["system"])
async def ready():
    pool = await store.pool()
    async with pool.acquire() as conn:
        await conn.fetchval("SELECT 1")
    return {"status": "ok", "policy": load_policy()["version"]}


@router.get("/catalog", tags=["catalog"])
async def get_catalog():
    """Продукты, цели, отрасли с отраслевыми спредами и ключевая ставка — для подбора и «почему так»."""
    pol = load_policy()
    market = pol["market"]
    sections = {code: {**sec, "spread": {b: catalog.industry_spread(market, code, b) for b in ("short", "long")}}
                for code, sec in pol["sections"].items()}
    return plain({"policyVersion": pol["version"], "keyRate": market["key_rate"], "goals": pol["goals"],
                  "products": pol["products"], "sections": sections, "alternatives": pol["alternatives"]})


class LoanCalcIn(BaseModel):
    amount: Decimal = Field(gt=0)
    term_months: int = Field(gt=0, le=120)
    rate: Decimal | None = Field(None, gt=0, description="% годовых; без ставки — посчитаем по отрасли и классу риска")
    product: Product = "EXPRESS"
    section: str | None = Field(None, pattern=r"^[A-U]$")
    risk_class: Literal["A", "B", "C", "D"] = "B"
    segment: Literal["IP", "LLC", "JSC"] = "IP"


@router.post("/calc/loan", tags=["catalog"])
async def calc_loan(body: LoanCalcIn):
    """Калькулятор: ставка (если не задана), платёж, переплата, график."""
    pol = load_policy()
    product = pol["products"][body.product]
    rate_parts = None
    if body.rate is None:
        rate_parts = catalog.rate(pol, body.section, body.term_months, body.risk_class,
                                  catalog.security_for(product, body.segment))
    rate = body.rate or rate_parts["total"]
    pay = calc.payment(product["repayment"], body.amount, rate, body.term_months)
    schedule = calc.annuity_schedule(body.amount, rate, body.term_months) if product["repayment"] == "annuity" else []
    total = sum((r["payment"] for r in schedule), Decimal(0)) if schedule else pay * body.term_months + body.amount
    return plain({"rate": rate, "rateParts": rate_parts, "repayment": product["repayment"], "payment": pay,
                  "overpayment": calc.money(total - body.amount), "schedule": schedule})


@router.get("/companies/{inn}/profile", tags=["company"])
async def profile(inn: Inn):
    """Что банк знает о компании: факты и откуда каждый источник, с датой и статусом."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        facts, provenance = await company.facts(conn, inn)
    if not provenance:
        raise HTTPException(404, "по компании ещё нет данных — POST /companies/{inn}/refresh")
    return plain({"facts": facts, "sources": provenance})


@router.post("/companies/{inn}/refresh", status_code=202, tags=["company"])
async def refresh(inn: Inn):
    """Запросить свежие данные из реестров и банка (делает worker). БКИ здесь не запрашивается — только в заявке."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        await store.enqueue(conn, "refresh_company", {"inn": inn})
    return {"status": "queued"}


@router.get("/companies/{inn}/products", tags=["company"])
async def products(inn: Inn, goal: Goal, amount: Annotated[Decimal, Query(gt=0)],
                   term_months: Annotated[int | None, Query(gt=0, le=120)] = None):
    """Подбор: продукты под цель с меткой «предодобрено / условно / рассмотрение / недоступно» и условиями."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        facts, provenance = await company.facts(conn, inn)
    if not provenance:
        raise HTTPException(404, "по компании ещё нет данных — POST /companies/{inn}/refresh")
    return plain({"items": engine.preapprove(facts, load_policy(), goal, amount, term_months)})


class ApplicationIn(BaseModel):
    inn: str = Field(pattern=r"^\d{10}$|^\d{12}$")
    product: Product
    amount: Decimal = Field(gt=0)
    term_months: int | None = Field(None, gt=0, le=120)
    goal: Goal | None = None
    consent_bki: bool = Field(False, description="согласие на запрос КИ (218-ФЗ ст. 6 ч. 9)")
    corporate_approval: bool = Field(False, description="решение участников о крупной сделке уже есть")
    collateral_value: Decimal | None = Field(None, gt=0)


@router.post("/applications", status_code=201, tags=["application"])
async def create_application(body: ApplicationIn):
    request = body.model_dump(exclude={"inn", "consent_bki"}, exclude_none=True)
    pool = await store.pool()
    async with pool.acquire() as conn:
        app = await store.create_application(conn, body.inn, {"request": request, "consent_bki": body.consent_bki}, "client")
    return plain(app)


@router.get("/applications/{app_id}", tags=["application"])
async def get_application(app_id: UUID):
    pool = await store.pool()
    async with pool.acquire() as conn:
        app = await store.get_application(conn, app_id)
    if app is None:
        raise HTTPException(404, "заявка не найдена")
    return plain(app)


@router.post("/applications/{app_id}/submit", tags=["application"])
async def submit(app_id: UUID, idempotency_key: Annotated[str | None, Header()] = None):
    """Подать: DRAFT → SUBMITTED и задача конвейера в той же транзакции. Повтор с тем же ключом не создаёт дублей."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        app = await store.get_application(conn, app_id)
        if app is None:
            raise HTTPException(404, "заявка не найдена")
        if app["status"] != "DRAFT":
            return plain(app)
        async with conn.transaction():
            app = await store.move(conn, app, "SUBMITTED", "client", reason="подана",
                                   idempotency_key=idempotency_key)
            await store.enqueue(conn, "pipeline", application_id=app_id)
    return plain(app)


@router.get("/applications/{app_id}/events", tags=["application"])
async def application_events(app_id: UUID):
    pool = await store.pool()
    async with pool.acquire() as conn:
        return plain({"items": await store.events(conn, app_id)})
