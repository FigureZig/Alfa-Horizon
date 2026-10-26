"""Клиентский путь: кто я и мои компании, главная, что банк знает о компании, подбор, заявка от черновика до выдачи.

Права проверяются на каждый запрос по снапшотам (deps.require): смотреть — любая связь с компанией, готовить и подавать —
руководитель или ДБО с правом подготовки, подписывать — руководитель без блокировок или ИП (docs/05 §3).
"""

import asyncio
import json
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Header, Path, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from .. import clock, company, lifecycle, personas, store
from ..domain import calc, catalog, engine, levers, matching
from ..domain.scoring import explain_factor
from ..domain.state import TERMINAL
from ..features import cash_flow, person_links
from ..jsonutil import plain
from ..policy import load as load_policy
from . import schemas as S
from . import views
from .deps import Me, access, require, voter
from .http import Problem, ok
from .schemas import doc

router = APIRouter()
Inn = Annotated[str, Path(pattern=r"^\d{10}$|^\d{12}$", description="ИНН: 10 цифр — юрлицо, 12 — ИП")]
Lang = Annotated[Literal["ru", "en"], Query(description="язык текстов")]
Product = Literal["OVERDRAFT", "EXPRESS", "WORKING_CAPITAL", "INVESTMENT", "CONTRACT", "AGRO_SEASONAL"]
Goal = Literal["cash_gap", "stock", "equipment", "growth", "contract"]


@router.get("/health/live", tags=["system"], **doc(S.HealthResponse, summary="Сервис жив"))
async def live():
    """Процесс API отвечает. Для проверки живости в оркестраторе."""
    return ok({"status": "ok"})


@router.get("/health/ready", tags=["system"], **doc(S.HealthResponse, summary="Готов к работе: база и политика на месте"))
async def ready():
    """API готово обслуживать: база доступна, политика загружена; в ответе — версия политики с хэшем файлов."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        await conn.fetchval("SELECT 1")
    return ok({"status": "ok", "policy": load_policy()["version"]})


# ── каталог и калькулятор ────────────────────────────────────────────────────────────────────────────────────────


@router.get("/catalog", tags=["catalog"], **doc(S.CatalogResponse, summary="Продукты, цели, отрасли и ключевая ставка"))
async def get_catalog():
    """Продукты, цели, отрасли с отраслевыми спредами и ключевая ставка — для подбора и «почему так»."""
    pol = load_policy()
    market = pol["market"]
    sections = {code: {**sec, "spread": {b: catalog.industry_spread(market, code, b) for b in ("short", "long")}}
                for code, sec in pol["sections"].items()}
    return ok({"policy_version": pol["version"], "key_rate": market["key_rate"], "goals": pol["goals"],
               "products": pol["products"], "sections": sections, "alternatives": pol["alternatives"]})


DECISION_TEXT = {"ru": {"auto": "решение за минуту — система решает сама до {limit} ₽",
                        "specialist": "решает кредитный специалист"},
                 "en": {"auto": "a decision in a minute — automatic up to ₽{limit}", "specialist": "a loan specialist decides"}}


@router.get("/catalog/products", tags=["catalog"],
            **doc(S.ProductCatalogResponse, 422, summary="Продукты для витрины: ставка «от», сумма, срок, кто решает"))
async def catalog_products(lang: Lang = "ru"):
    """Карточки продуктов для главной страницы и подбора. Ставка «от» — лучшая по политике: ключевая ставка, минимальный
    отраслевой спред среди разделов, где продукт доступен, и спред класса A с обеспечением продукта; сумма и срок — границы
    продукта; кто решает — по политике класса A и порогу автоматического решения."""
    pol = load_policy()
    limit = f"{pol['params']['auto_authority_max']:,}".replace(",", " " if lang == "ru" else ",")
    cards = []
    for code, product in pol["products"].items():
        sections = [k for k, sec in pol["sections"].items() if code in sec.get("products", []) and not sec.get("stop")]
        quotes = [catalog.rate(pol, section, term, "A", catalog.security_for(product, segment))
                  for section in sections for segment in product["segments"]
                  for term in {product["term_months"]["min"], product["term_months"]["max"]}]
        best = min(quotes, key=lambda q: q["total"])
        decision = "auto" if product["class_policy"]["A"] == "auto" else "specialist"
        cards.append({"id": code, "name": product["name"] if lang == "ru" else product.get("name_en", product["name"]),
                      "benefits": product.get("benefits", {}).get(lang, []),
                      "amount_min": float(product["amount"]["min"]), "amount_max": float(product["amount"]["max"]),
                      "term_months_min": product["term_months"]["min"], "term_months_max": product["term_months"]["max"],
                      "rate_from": float(best["total"]),
                      "rate_parts": {k: float(best[k]) for k in ("key_rate", "industry", "risk")},
                      "repayment": product["repayment"], "decision": decision,
                      "decision_text": DECISION_TEXT[lang][decision].format(limit=limit),
                      "goals": [g for g, goal in pol["goals"].items() if code in goal["products"]], "law": product.get("law")})
    return ok({"policy_version": pol["version"], "key_rate": pol["market"]["key_rate"], "products": cards})


class LoanCalcIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [
        {"amount": 1000000, "term_months": 12, "product": "EXPRESS", "section": "I", "risk_class": "B"}]})
    amount: Decimal = Field(gt=0)
    term_months: int = Field(gt=0, le=120)
    rate: Decimal | None = Field(None, gt=0, description="% годовых; без ставки — посчитаем по отрасли и классу риска")
    product: Product = "EXPRESS"
    section: str | None = Field(None, pattern=r"^[A-U]$")
    risk_class: Literal["A", "B", "C", "D"] = "B"
    segment: Literal["IP", "LLC", "JSC"] = "IP"


@router.post("/calc/loan", tags=["catalog"], **doc(S.LoanCalcResponse, 422, summary="Калькулятор: платёж, переплата и график"))
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
    if product["repayment"] == "revolving":      # у лимита нет графика: проценты — за занятую сумму и дни, а не за срок
        days = 10
        interest = calc.overdraft_interest(body.amount, rate, days)
        return ok({"rate": rate, "rate_parts": rate_parts, "repayment": "revolving", "payment": pay, "overpayment": None,
                   "schedule": [], "usage_example": {
                       "amount": body.amount, "days": days, "interest": interest,
                       "text": f"Займёте весь лимит на {days} дней — проценты {_rub(interest, 'ru')}; {_rub(pay, 'ru')} "
                               "в месяц — только если лимит занят целиком весь месяц. Долг гасится сам из поступлений"}})
    schedule = calc.annuity_schedule(body.amount, rate, body.term_months) if product["repayment"] == "annuity" else []
    total = sum((r["payment"] for r in schedule), Decimal(0)) if schedule else pay * body.term_months + body.amount
    return ok({"rate": rate, "rate_parts": rate_parts, "repayment": product["repayment"], "payment": pay,
               "overpayment": calc.money(total - body.amount), "schedule": schedule})


# ── кто я ────────────────────────────────────────────────────────────────────────────────────────────────────────


async def my_companies(conn, who) -> tuple[list[dict], bool]:
    """Компании человека — из карточки клиента в банке (доступы ДБО), права — из реестров по каждой."""
    if who.kind == "bank":
        return [], False
    card = (await store.snapshots(conn, who.inn)).get("bank_person")
    if card is None or card["payload"] is None:
        return [], True
    out = []
    for link in person_links(card["payload"]):
        facts, provenance = await company.facts(conn, link["inn"])
        if not provenance:
            out.append({"inn": link["inn"], "loaded": False, "bank_access": link["level"]})
            continue
        granted = (await access(conn, who, link["inn"]))[0]
        out.append({"inn": link["inn"], "loaded": True, "name": facts.get("name"), "short_name": facts.get("short_name"),
                    "segment": facts.get("segment"),
                    "okved": facts.get("okved"), "bank_access": link["level"], **granted})
    return out, any(not c["loaded"] for c in out)


async def active_company(conn, who) -> str | None:
    persona = await personas.get(conn, who.persona_id)
    default = persona["companies"][0]["inn"] if persona and persona["kind"] == "client" else None
    return await store.kv_get(conn, f"session:{who.persona_id}:company", default)


@router.get("/me", tags=["me"], **doc(S.MeResponse, 401, summary="Кто я: пользователь и его компании с правами"))
async def me(who: Me, lang: Lang = "ru"):
    """Кто вошёл, его компании с правами и почему (роли из ЕГРЮЛ/ЕГРИП и ДБО) и активная компания."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        persona = await personas.get(conn, who.persona_id)
        companies, loading = await my_companies(conn, who)
        active = await active_company(conn, who)
    return ok({"persona": personas.card(persona, lang), "actor": {"kind": who.kind, "inn": who.inn, "name": who.name},
               "companies": companies, "active_company_inn": active, "loading": loading})


class ActiveCompanyIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"inn": "7701000040"}]})
    inn: str = Field(pattern=r"^\d{10}$|^\d{12}$")


@router.put("/me/company", tags=["me"], **doc(S.ActiveCompanyResponse, 401, 403, 409, summary="Переключить активную компанию"))
async def switch_company(body: ActiveCompanyIn, who: Me):
    """Переключить компанию: только ту, с которой у человека есть связь."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        await require(conn, who, body.inn, "view")
        await store.kv_set(conn, f"session:{who.persona_id}:company", body.inn)
    return ok({"active_company_inn": body.inn})


# ── компания ─────────────────────────────────────────────────────────────────────────────────────────────────────


@router.get("/companies/{inn}/capabilities", tags=["company"],
            **doc(S.RightsResponse, 401, 409, summary="Мои права в компании и почему"))
async def capabilities(inn: Inn, who: Me):
    """Что вам можно в этой компании и почему — с нормой закона (docs/05 §3)."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        granted, _, _ = await access(conn, who, inn)
    return ok(granted)


@router.post("/companies/{inn}/refresh", status_code=202, tags=["company"],
             **doc(S.StatusResponse, 401, 403, status=202, summary="Обновить данные компании из реестров"))
async def refresh(inn: Inn, who: Me):
    """Запросить свежие данные из реестров и банка (делает worker). БКИ здесь не запрашивается — только в заявке."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        _, provenance = await company.facts(conn, inn)
        if provenance:
            await require(conn, who, inn, "view")
        await store.enqueue(conn, "refresh_company", {"inn": inn})
    return ok({"status": "queued"})


def quick_offer(facts: dict, pol: dict) -> dict | None:
    """«Предложение в 1 клик» (K2, docs/03): лучший предодобренный продукт под кассовый разрыв, сумма — от оборотов."""
    if not facts.get("inflow_avg"):
        return None
    params = pol["params"]
    amount = calc.floor_to(Decimal(facts["inflow_avg"]) * Decimal(params["k_overdraft"]), params["amount_step_small"])
    for item in engine.preapprove(facts, pol, "cash_gap", max(amount, Decimal(100_000))):
        offer = item["decision"]["offer"]
        if item["label"] == "PREAPPROVED" and offer:
            return {"label": item["label"], "product": offer["product"], "product_name": offer["product_name"],
                    "amount": offer["amount"], "term_months": offer["term_months"], "rate": offer["rate"]["total"],
                    "payment": offer["payment"], "goal": "cash_gap"}
    return None


@router.get("/dashboard", tags=["company"],
            **doc(S.DashboardResponse, 401, 403, 409, 422, summary="Главная: остаток, обороты, предложение в 1 клик"))
async def dashboard(who: Me, company_inn: Annotated[str | None, Query(pattern=r"^\d{10}$|^\d{12}$")] = None):
    """Главная: остаток, приход и расход за текущий месяц, активные кредиты, денежный поток за 6 месяцев,
    последние операции и предодобренное предложение. Без company_inn — активная компания."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        inn = company_inn or await active_company(conn, who)
        if inn is None:
            raise Problem(422, "COMPANY_REQUIRED", "укажите company_inn")
        _, facts = await require(conn, who, inn, "view")
        tx = (await store.snapshots(conn, inn)).get("bank_tx")
        flow = cash_flow(tx["payload"] if tx else None, await clock.today(conn))
        ours = sum(1 for a in await store.applications(conn, inn) if a["status"] == "ISSUED")
    if flow is None:
        raise Problem(409, "COMPANY_NOT_LOADED", "выписки по счёту ещё нет — банк её загружает", inn=inn)
    return ok({
        "company": {"inn": inn, "name": facts.get("name"), "segment": facts.get("segment")},
        "total_balance": flow["balance"], "monthly_income": flow["current"]["income"],
        "monthly_expenses": flow["current"]["expenses"], "active_loans_count": (facts.get("active_credits") or 0) + ours,
        "cash_flow": flow["months"], "current_month": flow["current"], "recent_transactions": flow["recent"],
        "offer": quick_offer(facts, load_policy()), "as_of": flow["as_of"]})


# ── заявки ───────────────────────────────────────────────────────────────────────────────────────────────────────


class ApplicationIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [
        {"inn": "770100000079", "product": "OVERDRAFT", "amount": 400000, "term_months": 12, "goal": "cash_gap",
         "consent_bki": True}]})
    inn: str = Field(pattern=r"^\d{10}$|^\d{12}$")
    product: Product | None = Field(None, description="нет — банк подберёт продукт под цель по данным компании (нужен goal)")
    amount: Decimal = Field(gt=0)
    term_months: int | None = Field(None, gt=0, le=120)
    goal: Goal | None = None
    consent_bki: bool = Field(False, description="согласие на запрос КИ (218-ФЗ ст. 6 ч. 9)")
    corporate_approval: bool = Field(False, description="решение участников о крупной сделке уже есть")
    collateral_value: Decimal | None = Field(None, gt=0)


async def _app_for(conn, who, app_id: UUID, right: str) -> tuple[dict, dict]:
    app = await lifecycle.load(conn, app_id)
    if right == "view":                          # участник видит заявку, где его просят голосовать, — и только её
        granted, _, _ = await access(conn, who, app["company_inn"])
        if granted["can"]["view"] or voter(app, who, granted):
            return app, granted
    granted, _ = await require(conn, who, app["company_inn"], right)
    return app, granted


def _view(app: dict, granted: dict, who) -> dict:
    return views.application(app, granted["can"], role=who.role, person_inn=who.inn)


@router.get("/applications", tags=["application"], **doc(S.ApplicationsResponse, 401, 403, 409, 422, summary="Заявки компании"))
async def list_applications(who: Me, company_inn: Annotated[str | None, Query(pattern=r"^\d{10}$|^\d{12}$")] = None):
    """Заявки компании, новые сверху. Без company_inn — активной компании пользователя."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        inn = company_inn or await active_company(conn, who)
        if inn is None:
            raise Problem(422, "COMPANY_REQUIRED", "укажите company_inn")
        granted, _ = await require(conn, who, inn, "view")
        rows = await store.applications(conn, inn)
    return ok([_view(a, granted, who) for a in rows])


@router.post("/applications", status_code=201, tags=["application"],
             **doc(S.ApplicationResponse, 401, 403, 409, 422, status=201, summary="Создать заявку (черновик)"))
async def create_application(body: ApplicationIn, who: Me):
    """Создать черновик заявки: продукт, сумма, срок, цель и согласие на запрос кредитной истории (218-ФЗ ст. 6 ч. 9). Готовить
    заявку может руководитель или пользователь ДБО с правом подготовки."""
    request = body.model_dump(exclude={"inn", "consent_bki"}, exclude_none=True)
    pool = await store.pool()
    async with pool.acquire() as conn:
        granted, facts = await require(conn, who, body.inn, "prepare")
        if body.product is None:                 # от задачи: продукт выбирает банк тем же подбором, что и /offers
            chosen = _product_for(facts, body)
            limit = matching.limit_for(load_policy()["products"][chosen], body.amount)
            request.update(product=chosen, product_chosen_by="bank", amount=limit,
                           **({"need": body.amount} if limit != body.amount else {}))   # лимит овердрафта ≥ минимума
        app = await lifecycle.create(conn, body.inn, request, body.consent_bki, who.label,
                                     {"persona": who.persona_id, "inn": who.inn, "name": who.name},
                                     facts.get("short_name") or facts.get("name"))
    return ok(_view(app, granted, who))


def _product_for(facts: dict, body: ApplicationIn) -> str:
    if body.goal is None:
        raise Problem(422, "GOAL_REQUIRED", "без продукта нужна цель — банк подберёт продукт под неё")
    found = matching.match(facts, load_policy(), body.goal, body.amount, body.term_months)
    chosen = found["recommended"] or next((o["product"] for o in found["options"] if o["available"]), None)
    if chosen is None:
        raise Problem(422, "NO_PRODUCT_FOR_GOAL", "под эту задачу банк сейчас ничего не предложит",
                      blockers=found["blockers"], why={o["product"]: o["why"] for o in found["options"]})
    return chosen


@router.get("/applications/{app_id}", tags=["application"],
            **doc(S.ApplicationResponse, 401, 403, 404, summary="Заявка: статус, решение, оферта и кнопки"))
async def get_application(app_id: UUID, who: Me):
    """Заявка целиком: статус, флаги, решение с причинами, оферта и варианты, подписи, выдача, срок статуса и available_actions —
    кнопки, которые этот пользователь может нажать сейчас."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        app, granted = await _app_for(conn, who, app_id, "view")
    return ok(_view(app, granted, who))


@router.post("/applications/{app_id}/submit", tags=["application"],
             **doc(S.ApplicationResponse, 401, 403, 404, 409, summary="Подать заявку"))
async def submit(app_id: UUID, who: Me, idempotency_key: Annotated[str | None, Header()] = None):
    """Подать: DRAFT → SUBMITTED и задача конвейера в той же транзакции. Повтор с тем же ключом не создаёт дублей."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        app, granted = await _app_for(conn, who, app_id, "prepare")
        app = await lifecycle.submit(conn, app, who.label, idempotency_key)
    return ok(_view(app, granted, who))


@router.post("/applications/{app_id}/withdraw", tags=["application"],
             **doc(S.ApplicationResponse, 401, 403, 404, 409, summary="Отозвать заявку"))
async def withdraw(app_id: UUID, who: Me):
    """Отозвать до выдачи; после подписи — отказ от получения (ГК ст. 821 п. 2)."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        app, granted = await _app_for(conn, who, app_id, "prepare")
        app = await lifecycle.withdraw(conn, app, who.label)
    return ok(_view(app, granted, who))


class AcceptIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"variant": 0}]})
    variant: int = Field(0, ge=0, description="0 — основной вариант, 1… — альтернативы из offers")


@router.post("/applications/{app_id}/offer/accept", tags=["application"],
             **doc(S.ApplicationResponse, 401, 403, 404, 409, 422, summary="Принять оферту (основной вариант или альтернативу)"))
async def accept_offer(app_id: UUID, who: Me, body: AcceptIn | None = None):
    """Принять оферту: variant 0 — основной вариант, 1… — альтернативы из offers. Заявка переходит к подписи; подписантов
    определяет ЕГРЮЛ/ЕГРИП."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        app, granted = await _app_for(conn, who, app_id, "prepare")
        app = await lifecycle.accept_offer(conn, app, who.label, (body or AcceptIn()).variant)
    return ok(_view(app, granted, who))


@router.post("/applications/{app_id}/offer/decline", tags=["application"],
             **doc(S.ApplicationResponse, 401, 403, 404, 409, summary="Отказаться от оферты"))
async def decline_offer(app_id: UUID, who: Me):
    """Отказаться от оферты — заявка закрывается (DECLINED)."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        app, granted = await _app_for(conn, who, app_id, "prepare")
        app = await lifecycle.decline_offer(conn, app, who.label)
    return ok(_view(app, granted, who))


@router.post("/applications/{app_id}/signatures", tags=["application"],
             **doc(S.ApplicationResponse, 401, 403, 404, 409, summary="Подписать договор в кабинете"))
async def sign(app_id: UUID, who: Me):
    """Подписать договор (ПЭП в ДБО). Совместные руководители — подписан, когда подписали все."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        app, granted = await _app_for(conn, who, app_id, "sign")
        role = {"self": "owner", "poa": "poa"}.get(granted["sign_mode"], "eio")    # кем подписан: сам, ЕИО или по МЧД
        app = await lifecycle.sign(conn, app, who.label, {"inn": who.inn, "fio": who.name, "role": role})
    return ok(_view(app, granted, who))


class InfoAnswerIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [
        {"documents": ["Пояснения к отчётности.pdf"], "comment": "Пояснения по запросу специалиста"}]})
    corporate_approval: bool = Field(False, description="решение участников о крупной сделке принято")
    collateral_value: Decimal | None = Field(None, gt=0, description="стоимость залога, ₽")
    documents: list[str] = Field(default_factory=list, description="названия загруженных документов")
    comment: str | None = Field(None, max_length=2000)


@router.post("/applications/{app_id}/info-requests/answer", tags=["application"],
             **doc(S.ApplicationResponse, 401, 403, 404, 409, 422, summary="Ответить на запрос банка"))
async def answer_info(app_id: UUID, body: InfoAnswerIn, who: Me):
    """Ответить на запрос банка: решение участников о крупной сделке, стоимость залога или документы. Заявка возвращается на
    проверку или к специалисту."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        app, granted = await _app_for(conn, who, app_id, "prepare")
        app = await lifecycle.answer_info(conn, app, who.label, body.model_dump(exclude_none=True))
    return ok(_view(app, granted, who))


LEVERS = {
    "pay_tax_debt": ("погасить налоговую недоимку", "pay off the tax arrears"),
    "reduce_debt": ("досрочно погасить часть кредитов — снизить платежи", "repay part of existing loans early"),
    "move_turnover": ("перевести обороты в банк", "move turnover to this bank"),
    "wait_age": ("подать, когда бизнесу исполнится год", "apply when the business turns one"),
    "wait_requests": ("подать через 30 дней без новых запросов в БКИ", "apply in 30 days without new bureau inquiries"),
    "amount_down": ("взять меньшую сумму", "take a smaller amount"),
    "term_up": ("взять на больший срок — платёж меньше", "take a longer term for a lower payment"),
    "guarantor": ("привести поручителя", "bring a guarantor"),
}


PATH = {   # заголовок пути по исходу: у одобренной заявки рычаги улучшают условия, у встречного — дают всю сумму
    "approval": ("Как получить одобрение", "How to get approved"),
    "full_amount": ("Как получить всю сумму", "How to get the full amount"),
    "better_terms": ("Как улучшить условия", "How to improve the terms"),
}
NO_DATA = {"ru": "нет данных — банк спросит", "en": "no data — the bank will ask"}


def _rub(value, lang: str) -> str:
    amount = f"{int(Decimal(str(value))):,}"
    return f"{amount.replace(',', ' ')} ₽" if lang == "ru" else f"₽{amount}"


def _caps(decision: dict, offer: dict, pol: dict, lang: str) -> list[dict]:
    """Ограничения суммы с суммами: какой лимит сработал, видно без расчётов на фронте."""
    out = []
    for cap in decision.get("caps") or []:
        title = pol["reasons"].get(cap["code"], cap["code"])
        value = NO_DATA[lang] if cap["value"] is None else _rub(cap["value"], lang)
        out.append({**cap, "title": title, "text": f"{title}: {value}", "binding": cap["code"] == offer.get("binding_cap")})
    return out


def _price_parts(rate: dict) -> list[dict]:
    return [{"part": "key_rate", "value": rate.get("key_rate"), "text": "ключевая ставка Банка России"},
            {"part": "industry", "value": rate.get("industry"),
             "text": f"отраслевой спред раздела {rate.get('section')}: ставка по отрасли минус средняя по МСП (бюллетень ЦБ)"},
            {"part": "risk", "value": rate.get("risk"),
             "text": f"спред за риск класса {rate.get('risk_class')}: ожидаемые потери PD × LGD плюс 1,5 п.п."}]


def explanation(decision: dict, facts: dict, request: dict, pol: dict, lang: str = "ru") -> dict:
    """«Почему так» по решению: вклад каждого фактора и интервалы карты, PD и класс, ставка из частей, лимит из
    ограничений; путь к одобрению (K3) — на сегодняшних фактах."""
    card, risk, offer = pol["scorecard"], decision.get("risk") or {}, decision.get("offer") or {}
    factors = []
    for c in risk.get("contributions", []):
        spec = card["factors"][c["factor"]]
        c = {"effect": "unknown" if c["value"] is None else "minus" if c["points"] < 0 else "plus" if c["points"] > 0
             else "neutral", **c}                          # решения до этой версии хранились без effect
        factors.append({**explain_factor(c, card, pol["reasons"], lang), "fact": spec["fact"], "bins": spec["bins"],
                        "source": spec.get("source", "registry")})
    skip = () if facts.get("bki_known") else ("bki",)
    nxt = {x["factor"]: x for x in levers.factor_levers(facts, facts.get("segment"), card, skip)}
    for f in factors:
        f["next"] = nxt.get(f["factor"])
    rate = offer.get("rate") or {}
    product = pol["products"].get(offer.get("product") or request["product"], {})
    k3 = levers.path_to_approval(facts, request, decision, pol, engine.decide)
    for option in k3["options"]:
        option["title"] = " + ".join(LEVERS[n][0 if lang == "ru" else 1] for n in option["levers"])
    outcome = decision["outcome"]
    k3["kind"] = "better_terms" if outcome in ("APPROVE", "APPROVE_WITH_CONDITIONS") else \
        "full_amount" if outcome == "COUNTER_OFFER" else "approval"
    k3["title"] = PATH[k3["kind"]][0 if lang == "ru" else 1]
    return {
        "outcome": decision["outcome"], "status": decision["status"], "policy_version": decision["policy_version"],
        "reasons": decision["reasons"],
        "scoring": {"score": risk.get("score"), "pd": risk.get("pd"), "risk_class": risk.get("class"),
                    "best_class": risk.get("best_class"), "base": card["base"], "classes": card["classes"],
                    "pd_scale": card["pd_scale"], "factors": factors, "missing": risk.get("missing", [])},
        "price": {**rate, "parts": _price_parts(rate)} if rate else None,
        "limit": {"caps": _caps(decision, offer, pol, lang),
                  "binding": offer.get("binding_cap"), "amount": offer.get("amount"),
                  "class_multiplier": (product.get("class_multiplier") or {}).get(risk.get("class"))} if offer else None,
        "path_to_approval": k3,
    }


@router.get("/applications/{app_id}/explain", tags=["application"],
            **doc(S.ExplanationResponse, 401, 403, 404, 409, summary="Почему такое решение и как получить одобрение"))
async def explain(app_id: UUID, who: Me, lang: Lang = "ru"):
    """Почему решение такое: скоринг с вкладами и интервалами, ставка из частей, лимит из ограничений, путь к одобрению."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        app, _ = await _app_for(conn, who, app_id, "view")
        facts, _ = await company.facts(conn, app["company_inn"])
    decision = app["data"].get("decision")
    if not decision:
        raise Problem(409, "NOT_DECIDED", "по заявке ещё нет решения")
    return ok(explanation(decision, facts, app["data"]["request"], load_policy(), lang))


class VoteIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"vote": "for"}]})
    vote: Literal["for", "against"] = Field(description="голос участника: «за» или «против» крупной сделки")


@router.post("/applications/{app_id}/approvals/vote", tags=["application"],
             **doc(S.ApplicationResponse, 401, 403, 404, 409, 422, summary="Голос участника ООО за крупную сделку"))
async def vote(app_id: UUID, body: VoteIn, who: Me):
    """Голос участника ООО за крупную сделку (14-ФЗ ст. 46 п. 3): вес — доля, решение — большинство всех голосов."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        app, granted = await _app_for(conn, who, app_id, "approve")
        app = await lifecycle.vote(conn, app, who.label, {"inn": who.inn, "fio": who.name}, body.vote)
    return ok(_view(app, granted, who))


class EventStream(StreamingResponse):
    media_type = "text/event-stream"


def _sse(event: str, data, event_id: int | None = None) -> str:
    head = f"id: {event_id}\n" if event_id is not None else ""
    return f"{head}event: {event}\ndata: {json.dumps(plain(data), ensure_ascii=False)}\n\n"


STREAM_DOC = {"description": "Поток событий text/event-stream: первым — `snapshot` (статус, флаги, срок), дальше — записи "
                             "истории "
                             "с типом в `event` и номером в `id`; `: ping` раз в 15 с.",
              "content": {"text/event-stream": {"schema": {"type": "string"}, "example": (
                  'event: snapshot\ndata: {"status": "SUBMITTED", "flags": [], "deadline": null}\n\n'
                  'id: 7\nevent: application.status_changed\ndata: {"id": 7, "type": "application.status_changed", '
                  '"payload": {"from": "CHECKING", "to": "OFFERED"}}\n\n')}}}


@router.get("/applications/{app_id}/stream", tags=["application"], response_class=EventStream,
            summary="Живой таймлайн заявки (SSE)",
            responses={200: STREAM_DOC,
                       **{c: {"model": S.ProblemDetails, "description": S.ERRORS[c]} for c in (401, 403, 404)}})
async def stream(app_id: UUID, who: Me,
                 timeout_s: Annotated[float, Query(ge=1, le=600, description="через сколько секунд закрыть поток")] = 300,
                 last_event_id: Annotated[int | None, Header(description="переподключение: пропущенное после id")] = None,
                 lang: Lang = "ru"):
    """Server-Sent Events: каждая новая запись истории заявки приходит сразу — переход статуса, решение, подпись, событие
    реестра. Поток закрывается, когда заявка дошла до конца (ISSUED, REJECTED, DECLINED, WITHDRAWN, EXPIRED) или истёк
    timeout_s. Источник — NOTIFY из PostgreSQL после вставки в events, без опроса базы."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        app, _ = await _app_for(conn, who, app_id, "view")
        index = await personas.actor_index(conn, lang)

    async def events():
        conn = await store.listener()
        woke: asyncio.Queue = asyncio.Queue()

        def notified(_conn, _pid, _channel, payload: str) -> None:
            if json.loads(payload).get("application_id") == str(app_id):
                woke.put_nowait(True)

        await conn.add_listener("events", notified)
        try:
            yield _sse("snapshot", {"status": app["status"], "flags": app["flags"],
                                    "deadline": app["data"].get("deadline")})
            last = last_event_id if last_event_id is not None else \
                await conn.fetchval("SELECT coalesce(max(id), 0) FROM events WHERE application_id = $1", app_id)
            if last_event_id is not None:
                woke.put_nowait(True)                  # сразу отдать пропущенное
            loop = asyncio.get_running_loop()
            deadline = loop.time() + timeout_s
            while (left := deadline - loop.time()) > 0:
                try:
                    await asyncio.wait_for(woke.get(), timeout=min(15.0, left))
                except TimeoutError:
                    yield ": ping\n\n"
                    continue
                rows = await conn.fetch("SELECT id, at, type, actor, payload FROM events WHERE application_id = $1 AND id > $2 "
                                        "ORDER BY id", app_id, last)
                for row in rows:
                    last = row["id"]
                    yield _sse(row["type"], {**dict(row), "by": personas.actor_view(index, row["actor"], lang)}, row["id"])
                    if row["type"] == "application.status_changed" and row["payload"].get("to") in TERMINAL:
                        return
        finally:
            await conn.close()

    return EventStream(events(), headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/applications/{app_id}/events", tags=["application"],
            **doc(S.EventsResponse, 401, 403, 404, summary="История заявки"))
async def application_events(app_id: UUID, who: Me, lang: Lang = "ru"):
    """История заявки: переходы статусов, решения, подписи, события реестров — в порядке времени. `by` — кто сделал шаг:
    человек по имени (клиент или сотрудник банка) или «Банк» для шагов конвейера и сроков."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        await _app_for(conn, who, app_id, "view")
        index = await personas.actor_index(conn, lang)
        rows = await store.events(conn, app_id)
    return ok([{**row, "by": personas.actor_view(index, row["actor"], lang)} for row in rows])
