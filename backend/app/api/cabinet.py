"""Кабинет компании по ИНН — ручки в контракте фронта (frontend/src/app/types): главная, прогноз остатка (K1),
предодобренные продукты (K2), заявки и задачи, что банк знает о компании, кто работает в кабинете.

Суммы здесь — числа, как в DTO фронта: это витрина для отображения. Решения и заявки в ядре API держат деньги строкой.
Без токена кабинет компании открывает её пользователь (deps.current_actor) — так фронт входит по ИНН.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query

from seed import world

from .. import clock, company, lifecycle, personas, store
from ..config import settings
from ..domain import catalog, engine, forecast, levers, matching
from ..domain import repayment as repay
from ..domain.scoring import explain_factor
from ..features import INFLOW_SKIP, account_operations, person_links
from ..policy import load as load_policy
from . import schemas as S
from .deps import NO_RIGHT, Me, access, feature, require, voter
from .http import Problem, ok
from .schemas import doc

router = APIRouter(tags=["cabinet"])
Inn = Annotated[str, Path(pattern=r"^\d{10}$|^\d{12}$", description="ИНН компании: 10 цифр — юрлицо, 12 — ИП")]
Lang = Annotated[Literal["ru", "en"], Query(description="язык текстов")]
CURRENCY = "RUB"
TERMS = {"OVERDRAFT": 12, "EXPRESS": 36, "WORKING_CAPITAL": 24, "INVESTMENT": 60, "CONTRACT": 12, "AGRO_SEASONAL": 10}
CASH_GAP_PRODUCTS = ("OVERDRAFT", "EXPRESS")          # закрывают кассовый разрыв (цель cash_gap)
FRONT_STATUS = {"DRAFT": "DRAFT", "SUBMITTED": "SUBMITTED", "CHECKING": "IN_REVIEW", "UNDER_REVIEW": "IN_REVIEW",
                "INFO_REQUESTED": "ACTION_REQUIRED", "OFFERED": "APPROVED", "SIGNING": "ACTION_REQUIRED", "SIGNED": "APPROVED",
                "DISBURSING": "APPROVED", "ISSUED": "ISSUED", "REJECTED": "REJECTED"}   # DECLINED, WITHDRAWN, EXPIRED — закрыты
TASKS = {   # действие → (тип в контракте фронта, заголовок ru, заголовок en)
    "sign": ("SIGNATURE", "Подписать кредитный договор", "Sign the loan agreement"),
    "answer_info": ("DOCUMENT_REQUEST", "Ответить на запрос банка", "Respond to the bank's request"),
    "vote": ("DOCUMENT_REQUEST", "Проголосовать: согласие на крупную сделку", "Vote: consent to a major transaction"),
    "accept_offer": ("OFFER", "Рассмотреть предложение банка", "Review the bank's offer"),
    "submit": ("DRAFT", "Подать черновик заявки", "Submit the draft application"),
    "decide": ("REVIEW", "Рассмотреть заявку", "Review the application"),
    "confirm": ("CONFIRM", "Подтвердить решение — второй ключ", "Confirm the decision — second key"),
}
CARDS = {
    "ru": {"balance": "Остаток на счёте", "outflow": "Спишется до {date}", "inflow": "Поступит до {date}",
           "account": "Расчётный счёт ·· {tail}", "acquiring": "Эквайринг по картам покупателей",
           "customers": "Оплаты покупателей по договорам", "none": "Регулярных списаний нет",
           "credit_line": " · овердрафт до {limit} ₽"},
    "en": {"balance": "Account balance", "outflow": "Outgoing by {date}", "inflow": "Incoming by {date}",
           "account": "Current account ·· {tail}", "acquiring": "Card acquiring",
           "customers": "Customer payments under contracts",
           "none": "No regular payments", "credit_line": " · overdraft up to ₽{limit}"},
}


def num(x) -> float | None:
    return None if x is None else float(Decimal(x).quantize(Decimal("0.01")))


def _date(d, lang: str) -> str:
    return d.strftime("%d.%m") if lang == "ru" else d.strftime("%b %d")


async def _snapshot(conn, inn: str, source: str) -> dict | None:
    snap = (await store.snapshots(conn, inn)).get(source)
    return snap["payload"] if snap and snap["payload"] is not None else None


async def _forecast(conn, inn: str, facts: dict | None = None) -> dict | None:
    """K1 по выписке плюс кредиты, которые банк уже выдал: срочный — деньги на счёте и платёж каждый месяц,
    овердрафт — лимит, который прикрывает минус (в выписке их ещё нет)."""
    tx = await _snapshot(conn, inn, "bank_tx")
    if not tx:
        return None
    today, loans = await clock.today(conn), (facts or {}).get("own_loans", [])
    term = [loan for loan in loans if loan["repayment"] != "revolving"]
    balance = Decimal(tx["balance"]["amount"]) + sum((loan["amount"] for loan in term), Decimal(0))
    extra = [{"purpose": f"Платёж по кредиту {loan['number'] or ''}".strip(), "day": _payment_day(loan, today),
              "amount": loan["payment"], "repeats": 0} for loan in term]
    return forecast.forecast(account_operations(tx), balance, today, skip=INFLOW_SKIP, extra_regular=extra,
                             credit_line=(facts or {}).get("credit_line"))


def _payment_day(loan: dict, today) -> int:
    """Платёж по кредиту — в день выдачи каждого месяца."""
    issued = loan.get("disbursed_at")
    return datetime.fromisoformat(issued).astimezone(clock.TZ).day if issued else today.day


def _gap(fc: dict | None) -> dict | None:
    """Разрыв, который нужно закрывать: в пределах подключённого овердрафта минус уже прикрыт (COVERED)."""
    return fc["cash_gap"] if fc and fc["status"] == "CASH_GAP" else None


def _product_cards(facts: dict, gap: dict | None, lang: str) -> list[dict]:
    """K2: предодобренные продукты по данным банка и реестров; рекомендован тот, что закрывает найденный разрыв."""
    pol, out = load_policy(), []
    for code in catalog.available_products(pol, facts.get("section"), facts.get("segment")):
        product = pol["products"][code]
        request = {"product": code, "amount": product["amount"]["max"], "term_months": TERMS[code], "goal": None}
        d = engine.decide(facts, request, pol, "simulate", allow_alternative=False)
        offer = d["offer"]
        if d["outcome"] not in ("APPROVE", "COUNTER_OFFER", "APPROVE_WITH_CONDITIONS") or not offer:
            continue
        out.append({"id": f"{code.lower()}-{facts['inn']}", "product": code, "label": engine.PREAPPROVAL_LABEL[d["outcome"]],
                    "name": product["name"] if lang == "ru" else product.get("name_en", product["name"]),
                    "amount": num(offer["amount"]), "currency": CURRENCY, "rate": num(offer["rate"]["total"]),
                    "is_rate_from": not facts.get("bki_known"), "term_months": offer["term_months"],
                    "payment": num(offer["payment"]), "benefits": product.get("benefits", {}).get(lang, []),
                    "conditions": d["conditions"], "is_preliminary": True, "is_recommended": False})
    if gap:
        need = num(gap["amount"])
        fit = next((p for code in CASH_GAP_PRODUCTS for p in out if p["product"] == code and p["amount"] >= need), None)
        if fit:
            fit["is_recommended"] = True
    return out


# ── рабочее место банка по ИНН банка: фронт открывает кабинет специалиста так же, как кабинет компании ─────────────

BANK_CARDS = {
    "ru": {"review": "На рассмотрении", "review_d": "{n} · просрочен SLA: {late}", "second": "Ждут второго ключа",
           "second_d": "{n} выше {limit} ₽", "issued": "Выдано сегодня", "issued_d": "{n}"},
    "en": {"review": "Under review", "review_d": "{n} · SLA breached: {late}", "second": "Awaiting the second key",
           "second_d": "{n} above ₽{limit}", "issued": "Issued today", "issued_d": "{n}"},
}
COUNT = {"ru": {"app": ("заявка", "заявки", "заявок"), "loan": ("кредит", "кредита", "кредитов")},
         "en": {"app": ("application", "applications", "applications"), "loan": ("loan", "loans", "loans")}}


def _count(n: int, what: str, lang: str) -> str:
    """«1 заявка, 3 заявки, 5 заявок»; по-английски — единственное и множественное."""
    forms = COUNT[lang][what]
    if lang == "en":
        return f"{n} {forms[0] if n == 1 else forms[1]}"
    k = 0 if n % 10 == 1 and n % 100 != 11 else 1 if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else 2
    return f"{n} {forms[k]}"
BANK_PROFILE = {"legal_form": "JSC", "registered_at": None,
                "activity": {"okved_code": "64.19", "name": "Денежное посредничество прочее"}, "tax_regime": "OSN",
                "monthly_revenue": None, "currency": CURRENCY, "sources": [], "updated_at": None, "msp_category": None,
                "headcount": None, "facts": {}, "source_details": []}


def _is_bank(who, inn: str) -> bool:
    """ИНН банка открывает рабочее место сотрудника; клиенту туда нельзя."""
    if inn != personas.bank()["inn"]:
        return False
    if who.kind != "bank":
        raise Problem(403, "BANK_ONLY", "это рабочее место сотрудника банка")
    return True


def _amount(app: dict):
    data = app["data"]
    offer = (data.get("pending_decision") or {}).get("offer") or data.get("offer") or (data.get("decision") or {}).get("offer")
    return Decimal(str((offer or data["request"])["amount"]))


async def _bank_cards(conn, inn: str, lang: str) -> list[dict]:
    t, pol = BANK_CARDS[lang], load_policy()
    queue = await store.queue(conn)
    pending = [a for a in queue if a["data"].get("pending_decision")]
    today = await clock.today(conn)
    issued = [a for a in await store.queue(conn, ("ISSUED",))
              if (a["data"].get("loan") or {}).get("disbursed_at")
              and datetime.fromisoformat(a["data"]["loan"]["disbursed_at"]).astimezone(clock.TZ).date() == today]
    limit = f"{pol['params']['specialist_authority_max']:,}".replace(",", " ")
    late = sum("SLA_BREACH" in a["flags"] for a in queue)
    return [
        {"id": f"{inn}-review", "type": "balance", "title": t["review"], "amount": num(sum(map(_amount, queue), Decimal(0))),
         "currency": CURRENCY, "description": t["review_d"].format(n=_count(len(queue), "app", lang), late=late)},
        {"id": f"{inn}-second-key", "type": "outflow", "title": t["second"],
         "amount": num(sum(map(_amount, pending), Decimal(0))), "currency": CURRENCY,
         "description": t["second_d"].format(n=_count(len(pending), "app", lang), limit=limit)},
        {"id": f"{inn}-issued", "type": "inflow", "title": t["issued"],
         "amount": num(sum((Decimal(a["data"]["loan"]["amount"]) for a in issued), Decimal(0))),
         "currency": CURRENCY, "description": t["issued_d"].format(n=_count(len(issued), "loan", lang))},
    ]


def _contract_signal(facts: dict, cards: list[dict]) -> dict | None:
    """K5: действующий госконтракт, где компания поставщик, → кредит на исполнение: до 70% цены за вычетом аванса."""
    if "K5" not in settings.features or not facts.get("contracts"):
        return None
    k = max(facts["contracts"], key=lambda c: Decimal(str(c["price"])))
    return {"reg_num": k["regNum"], "customer": k["customer"], "price": num(k["price"]),
            "advance_percent": k.get("advancePercent", 0), "end_date": k["endDate"],
            "offer": next((p for p in cards if p["product"] == "CONTRACT"), None)}


@router.get("/companies/{inn}/insights", dependencies=[feature("K1")],
            **doc(S.InsightsResponse, 401, 403, 409, summary="K1 прогноз остатка и K2 предложение"))
async def insights(inn: Inn, who: Me, lang: Lang = "ru"):
    """K1 — прогноз остатка на 30 дней: точки по дням, самый глубокий разрыв и платежи, которые к нему ведут;
    K2 — предложение, которое этот разрыв закрывает. `cash_forecast` пустой, если выписки нет."""
    if _is_bank(who, inn):
        return ok({"inn": inn, "cash_forecast": None, "offer": None, "contract": None})
    pool = await store.pool()
    async with pool.acquire() as conn:
        _, facts = await require(conn, who, inn, "view")
        fc = await _forecast(conn, inn, facts)
    if fc is None:
        return ok({"inn": inn, "cash_forecast": None, "offer": None, "contract": None})
    gap = fc["cash_gap"]
    cards = _product_cards(facts, _gap(fc), lang)
    offer = next((p for p in cards if p["is_recommended"]), None)
    if offer and offer["product"] == "OVERDRAFT":     # сколько стоит закрыть разрыв: проценты только за дни в минусе
        cost = forecast.cover_cost(fc["points"], offer["rate"])
        offer["cover"] = cost and {"amount": num(cost["amount"]), "days": cost["days"], "interest": num(cost["interest"])}
    return ok({"inn": inn, "offer": offer, "contract": _contract_signal(facts, cards), "cash_forecast": {
        "status": fc["status"], "horizon_days": fc["horizon_days"], "currency": CURRENCY,
        "points": [{"date": p["date"], "balance": num(p["balance"])} for p in fc["points"]],
        "cash_gap": {"date": gap["date"], "amount": num(gap["amount"]), "first_negative_date": gap["first_negative_date"]}
        if gap else None,
        "credit_line": num(fc["credit_line"]),
        "operations": [{"id": f"op-{op['date']}-{abs(op['amount'])}", "date": op["date"], "title": op["title"],
                        "amount": num(op["amount"])} for op in fc["operations"]],
        "daily_inflow": num(fc["daily_inflow"]),
        "regular_outflows": [{"title": r["purpose"], "day": r["day"], "amount": num(r["amount"])}
                             for r in fc["regular_outflows"]],
    }})


@router.get("/companies/{inn}/score", dependencies=[feature("K3")],
            **doc(S.ScoreResponse, 401, 403, 404, 409, summary="Кредитное здоровье: балл, класс, вклады и рычаги"))
async def company_score(inn: Inn, who: Me, lang: Lang = "ru"):
    """Кредитное здоровье до заявки: балл, PD, класс, вклад каждого фактора и до какого значения его подтянуть.
    Без согласия на кредитную историю факторы полного отчёта БКИ не считаются (218-ФЗ ст. 6 ч. 9)."""
    if _is_bank(who, inn):
        raise Problem(404, "NOT_A_CLIENT", "у банка нет кредитного здоровья — это рабочее место сотрудника")
    pol = load_policy()
    pool = await store.pool()
    async with pool.acquire() as conn:
        _, facts = await require(conn, who, inn, "view")
    skip = () if facts.get("bki_known") else ("bki",) if facts.get("bki_info_known") else ("bki", "bki_info")
    result = levers.summary(facts, facts.get("segment"), pol["scorecard"], skip)
    result["contributions"] = [explain_factor(c, pol["scorecard"], pol["reasons"], lang) for c in result["contributions"]]
    return ok({"inn": inn, "bki_known": bool(facts.get("bki_known")), **result})


@router.get("/companies/{inn}/products", dependencies=[feature("K2")],
            **doc(S.ProductsResponse, 401, 403, 409, summary="Предодобренные продукты"))
async def products(inn: Inn, who: Me, lang: Lang = "ru"):
    """Предодобренные продукты (K2) — лимит, ставка, срок по данным банка и реестров; решение окончательное — по заявке."""
    if _is_bank(who, inn):
        return ok([])
    pool = await store.pool()
    async with pool.acquire() as conn:
        _, facts = await require(conn, who, inn, "view")
        fc = await _forecast(conn, inn, facts)
    return ok(_product_cards(facts, _gap(fc), lang))


NEEDS = {"ru": {"consent_bki": "согласие на запрос кредитной истории — без него условия предварительные",
                "corporate_approval": "согласие участников на крупную сделку (14-ФЗ ст. 46)",
                "collateral": "залог — укажете его стоимость в заявке", "guarantor": "поручитель (ГК ст. 361)",
                "specialist": "решение примет кредитный специалист"},
         "en": {"consent_bki": "consent to the credit history check — without it the terms are provisional",
                "corporate_approval": "the members' consent to a major transaction", "collateral": "collateral — you will "
                "state its value in the application", "guarantor": "a guarantor", "specialist": "a loan officer decides"}}
Goal = Literal["cash_gap", "stock", "equipment", "growth", "contract"]


@router.get("/companies/{inn}/offers", dependencies=[feature("K2")],
            **doc(S.OffersResponse, 401, 403, 409, summary="Подбор от задачи: что банк готов дать этой компании"))
async def offers(inn: Inn, who: Me, goal: Annotated[Goal | None, Query(description="на что деньги")] = None,
                 amount: Annotated[float | None, Query(gt=0, description="сколько нужно, ₽; нет — максимум продукта, "
                                                                         "для кассового разрыва — сумма разрыва")] = None,
                 term_months: Annotated[int | None, Query(ge=1, le=120, description="на сколько месяцев")] = None,
                 lang: Lang = "ru"):
    """Клиент говорит, на что нужны деньги, — банк по своим данным показывает продукты этой компании: доступен ли,
    сколько максимум, условия на нужную сумму (ставка своя, по классу риска и отрасли), что понадобится и почему нет.
    Без goal — весь каталог с личными ставками. Стоп-факторы компании — в blockers, с причиной."""
    if _is_bank(who, inn):
        raise Problem(404, "NOT_A_CLIENT", "подбор — для клиента, это рабочее место сотрудника")
    pool = await store.pool()
    async with pool.acquire() as conn:
        _, facts = await require(conn, who, inn, "view")
        fc = await _forecast(conn, inn, facts)
    gap = _gap(fc)
    if amount is None and goal == "cash_gap" and gap:          # «закрыть разрыв» — ровно на сумму разрыва
        amount = float(catalog.round_up(gap["amount"], load_policy()["params"]["amount_step_small"]))
    result = matching.match(facts, load_policy(), goal, amount, term_months)
    for option in result["options"]:
        option["needs"] = [{"code": n, "text": NEEDS[lang][n]} for n in option["needs"]]
        option["recommended"] = option["product"] == result["recommended"]
    return ok({"inn": inn, "goal": goal, "amount": amount, "term_months": term_months, "bki_known": bool(facts.get("bki_known")),
               "blockers": result["blockers"], "options": result["options"], "recommended": result["recommended"]})


REPAY_WHY = {
    "ru": {"fixed": "Фиксированный платёж {payment} ₽ — {share}% поступлений даже в три худших месяца: график комфортен",
           "from_inflows": "Фиксированный платёж {payment} ₽ — {share}% поступлений в худшие месяцы: удобнее гасить долей "
                           "поступлений, в слабый месяц платёж меньше"},
    "en": {"fixed": "A fixed payment of ₽{payment} is {share}% of inflows even in the three worst months: "
                    "the schedule is comfortable",
           "from_inflows": "A fixed payment of ₽{payment} is {share}% of inflows in the worst months: repaying a share "
                           "of inflows is easier, a weak month means a smaller payment"},
}


REPAY_SAVING = {
    "ru": ". Доля поступлений дешевле на {saving} ₽ и закроет долг за {months} мес., но в сильные месяцы платёж выше",
    "en": ". A share of inflows costs ₽{saving} less and repays in {months} months, but payments are higher in strong months",
}


@router.get("/companies/{inn}/repayment", dependencies=[feature("K4")],
            **doc(S.RepaymentResponse, 401, 403, 404, 409, 422, summary="K4: фиксированный график или доля поступлений"))
async def repayment(inn: Inn, who: Me, amount: Annotated[float, Query(gt=0, description="сумма кредита, ₽")],
                    term_months: Annotated[int, Query(ge=1, le=120, description="срок для графика, мес.")] = 12,
                    rate: Annotated[float | None, Query(gt=0, le=100, description="ставка, %; нет — по отрасли и классу "
                                                                                    "риска компании")] = None,
                    product: Annotated[str | None, Query(description="продукт: у овердрафта графика нет — сравнивать нечего")]
                    = None,
                    lang: Lang = "ru"):
    """Погашение из поступлений (K4): на истории счёта за 12 месяцев сравниваем фиксированный аннуитет и списание доли
    каждого поступления (не меньше минимума); стресс-тест — платёж к средним поступлениям трёх худших месяцев.
    Рекомендация и объяснение — для оферты; после выдачи списание идёт по договору (ГК ст. 854 п. 2)."""
    if _is_bank(who, inn):
        raise Problem(404, "NOT_A_CLIENT", "у банка нет графика погашения — это рабочее место сотрудника")
    pol = load_policy()
    if product and product in pol["products"] and pol["products"][product]["repayment"] != "annuity":
        raise Problem(422, "REPAYMENT_NOT_APPLICABLE", "у этого продукта нет графика платежей: овердрафт гасится сам из "
                      "поступлений, кредит под контракт — в конце срока", product=product)
    pool = await store.pool()
    async with pool.acquire() as conn:
        _, facts = await require(conn, who, inn, "view")
    if not facts.get("inflows_monthly"):
        raise Problem(409, "COMPANY_NOT_LOADED", "выписки по счёту ещё нет — банк её загружает", inn=inn)
    if rate is None:
        risk_class = levers.summary(facts, facts.get("segment"), pol["scorecard"])["class"]
        rate = float(catalog.rate(pol, facts.get("section"), term_months, risk_class, "none")["total"])
    params = pol["params"]
    plan = repay.compare(facts["inflows_monthly"], Decimal(str(amount)), Decimal(str(rate)), term_months,
                         share=str(params["k4_share"]), min_payment=str(params["k4_min_payment"]),
                         stress_max=str(params["k4_stress_max"]))
    fixed = plan["fixed"]
    why = REPAY_WHY[lang][plan["recommendation"]].format(
        payment=f"{fixed['payment']:,.0f}".replace(",", " " if lang == "ru" else ","),
        share=round((fixed["worst3_share"] or 0) * 100))
    saving = fixed["total_interest"] - plan["from_inflows"]["total_interest"]
    if plan["recommendation"] == "fixed" and saving > 0:      # дешевле — доля поступлений: честно говорим, чем платим
        why += REPAY_SAVING[lang].format(saving=f"{saving:,.0f}".replace(",", " " if lang == "ru" else ","),
                                         months=plan["from_inflows"]["months"] or "—")
    return ok({"inn": inn, "amount": amount, "rate": rate, "term_months": term_months,
               "fixed": {**fixed, "payment": num(fixed["payment"]), "total_interest": num(fixed["total_interest"]),
                         "worst3_inflow_avg": num(fixed["worst3_inflow_avg"])},
               "from_inflows": {**plan["from_inflows"], **{k: num(plan["from_inflows"][k]) for k in
                                                           ("min_payment", "total_interest", "max_payment", "min_paid")}},
               "recommendation": plan["recommendation"], "why": why, "stress_max": plan["stress_max"],
               "saving": num(max(saving, Decimal(0)))})


DATA_SOURCES = {"EGRUL": ("egrul",), "EGRIP": ("egrip",), "FNS": ("rsmp", "sshr", "paytax", "debtam", "snr"),
                "BANK_ACCOUNT": ("bank_tx",), "CREDIT_BUREAU": ("bki",)}   # у ИП реестр — ЕГРИП, у ООО и АО — ЕГРЮЛ


@router.get("/companies/{inn}/profile", **doc(S.ProfileResponse, 401, 403, 409, summary="Что банк знает о компании и откуда"))
async def profile(inn: Inn, who: Me, lang: Lang = "ru"):
    """Что банк знает о компании: форма, регистрация, деятельность, налоговый режим, обороты и из каких источников;
    плюс все факты с происхождением (для досье и «почему так»)."""
    if _is_bank(who, inn):
        bank = personas.bank()
        return ok({"inn": inn, "name": bank["name"] if lang == "ru" else bank["name_en"], **BANK_PROFILE})
    pool = await store.pool()
    async with pool.acquire() as conn:
        granted, facts, provenance = await access(conn, who, inn)
    if not granted["can"]["view"]:
        raise Problem(403, "FORBIDDEN", NO_RIGHT["view"], right="view", roles=granted["roles"])
    ok_sources = {p["source"] for p in provenance if p["used"]}
    fetched = [p["fetched_at"] for p in provenance if p["used"]]
    return ok({"inn": inn, "name": facts.get("name"), "legal_form": facts.get("segment"),
               "registered_at": facts.get("registered"),
               "activity": {"okved_code": facts["okved"], "name": facts.get("okved_name"),
                            "title": world.industry_title(facts["okved"], lang)} if facts.get("okved") else None,
               "tax_regime": facts.get("tax_regime"), "monthly_revenue": num(facts.get("inflow_avg")), "currency": CURRENCY,
               "sources": [k for k, names in DATA_SOURCES.items() if ok_sources & set(names)],
               "updated_at": max(fetched) if fetched else None, "msp_category": facts.get("msp_category"),
               "headcount": facts.get("headcount"), "facts": facts, "source_details": provenance})


async def tasks_for(conn, who, inn: str | None = None, lang: str = "ru") -> list[dict]:
    """Что ждёт этого пользователя: подписать, ответить, проголосовать, рассмотреть, подтвердить."""
    rows = []
    if who.kind == "bank":
        rows = [(app, None) for app in await store.queue(conn)]
    else:
        card = await _snapshot(conn, who.inn, "bank_person")
        persona = await personas.get(conn, who.persona_id)       # участник ООО связан с компанией реестром, не ДБО
        inns = [inn] if inn else list(dict.fromkeys([link["inn"] for link in person_links(card)]
                                                    + [c["inn"] for c in (persona or {}).get("companies", [])]))
        for company_inn in inns:
            facts, provenance = await company.facts(conn, company_inn)
            if not provenance:
                continue
            granted = (await access(conn, who, company_inn))[0]
            apps = await store.applications(conn, company_inn)
            if not granted["can"]["view"]:                       # без доступа к счёту — только где ждут его голос
                apps = [a for a in apps if voter(a, who, granted)]
            rows += [(app, granted["can"]) for app in apps]
    out = []
    for app, can in rows:
        for action in lifecycle.actions(app, can, role=who.role, person_inn=who.inn):
            if action not in TASKS or action == "withdraw":
                continue
            kind, ru, en = TASKS[action]
            due = (app["data"].get("deadline") or {}).get("at") if who.kind != "bank" else app["data"].get("sla_until")
            out.append({"id": f"{app['id']}:{action}", "type": kind, "action": action, "title": ru if lang == "ru" else en,
                        "due_date": due, "application_id": app["id"], "company_inn": app["company_inn"],
                        "status": app["status"]})
    return out


@router.get("/tasks", tags=["me"], **doc(S.TasksResponse, 401, summary="Входящие: что ждёт пользователя"))
async def my_tasks(who: Me, lang: Lang = "ru"):
    """Входящие пользователя по всем его компаниям (у банка — очередь): кнопка «перейти» ведёт в заявку."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        return ok(await tasks_for(conn, who, lang=lang))


@router.get("/companies/{inn}/applications/summary",
            **doc(S.ApplicationsSummaryResponse, 401, 403, 409, summary="Заявки и задачи для главной"))
async def applications_summary(inn: Inn, who: Me, lang: Lang = "ru"):
    """Заявки компании и задачи пользователя по ним — для главной.
    Статус укрупнённый, как во фронте; точный — в status_detail."""
    pol = load_policy()
    pool = await store.pool()
    async with pool.acquire() as conn:
        if _is_bank(who, inn):                   # у сотрудника — очередь банка
            rows, tasks = await store.queue(conn), await tasks_for(conn, who, lang=lang)
        else:
            granted, _, _ = await access(conn, who, inn)
            if not granted["can"]["view"] and not granted["can"]["approve"]:
                raise Problem(403, "FORBIDDEN", NO_RIGHT["view"], right="view", roles=granted["roles"])
            rows = await store.applications(conn, inn)
            if not granted["can"]["view"]:       # участник ООО — только заявки, где банк просит его голос
                rows = [a for a in rows if voter(a, who, granted)]
            tasks = await tasks_for(conn, who, inn, lang)
    apps = []
    for app in rows:
        if app["status"] not in FRONT_STATUS:
            continue
        offer = app["data"].get("offer") or (app["data"].get("decision") or {}).get("offer")
        code = (offer or app["data"]["request"])["product"]
        product = pol["products"][code]
        name = product["name"] if lang == "ru" else product.get("name_en", product["name"])
        apps.append({"id": app["id"], "product_name": name,
                     "amount": num((offer or app["data"]["request"])["amount"]), "currency": CURRENCY,
                     "status": FRONT_STATUS[app["status"]], "status_detail": app["status"], "flags": app["flags"],
                     "updated_at": app["updated_at"]})
    return ok({"applications": apps, "tasks": [t for t in tasks if t["type"] in ("SIGNATURE", "DOCUMENT_REQUEST")],
               "all_tasks": tasks})


async def _persona_for(conn, who, inn: str) -> dict:
    persona = await personas.get(conn, who.persona_id)
    if persona and (persona["kind"] == "bank" and inn == personas.bank()["inn"]
                    or any(c["inn"] == inn for c in persona.get("companies", []))):
        return persona
    found = await personas.for_company(conn, inn)
    if found is None:
        raise Problem(404, "COMPANY_NOT_FOUND", "в симуляторе нет компании с таким ИНН", inn=inn)
    return found


@router.get("/demo-personas/{inn}", **doc(S.CabinetUserResponse, 401, 404, summary="Кто работает в кабинете компании"))
async def cabinet_user(inn: Inn, who: Me, lang: Lang = "ru"):
    """Кто работает в кабинете компании (контракт фронта DemoPersonaDto): имя для приветствия и организация."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        persona = await _persona_for(conn, who, inn)
        today = await clock.today(conn)
    card = personas.card(persona, lang)
    first, last = card["full_name"].split(" ", 1)
    if persona["kind"] == "bank":
        organization = personas.bank()["name"] if lang == "ru" else personas.bank()["name_en"]
    else:
        main = next(c for c in persona["companies"] if c["inn"] == inn)
        organization = personas.short_name(main, lang) if lang == "en" else main["name"]
    return ok({"inn": inn, "first_name": first, "last_name": last, "initials": (first[:1] + last[:1]).upper(),
               "organization_name": organization, "user_id": persona["id"], "role": card["role"],
               "person_inn": card.get("person_inn"), "today": today})


@router.get("/demo-personas/{inn}/dashboard/summary",
            **doc(S.SummaryCardsResponse, 401, 403, 409, summary="Карточки главной: остаток, списания, поступления"))
async def dashboard_cards(inn: Inn, who: Me, lang: Lang = "ru"):
    """Карточки главной (контракт фронта DashboardSummaryCardDto): остаток сегодня, что спишется и что поступит до даты
    разрыва (или за 14 дней) — из того же прогноза K1."""
    t = CARDS[lang]
    pool = await store.pool()
    if _is_bank(who, inn):
        async with pool.acquire() as conn:
            return ok(await _bank_cards(conn, inn, lang))
    async with pool.acquire() as conn:
        _, facts = await require(conn, who, inn, "view")
        tx = await _snapshot(conn, inn, "bank_tx")
        fc = await _forecast(conn, inn, facts)
        today = await clock.today(conn)
    if fc is None:
        raise Problem(409, "COMPANY_NOT_LOADED", "выписки по счёту ещё нет — банк её загружает", inn=inn)
    until = fc["cash_gap"]["date"] if fc["cash_gap"] else today + timedelta(days=14)
    upcoming = [op for op in fc["upcoming"] if op["date"] <= until]
    titles = [op["title"] for op in sorted(upcoming, key=lambda op: op["amount"])]
    retail = any(item.get("category") == "acquiring" for item in tx["items"][-60:])
    return ok([
        {"id": f"{inn}-balance", "type": "balance", "title": t["balance"], "amount": num(fc["balance"]), "currency": CURRENCY,
         "description": t["account"].format(tail=tx["account"][-4:])
         + (t["credit_line"].format(limit=f"{int(fc['credit_line']):,}".replace(",", " ")) if fc["credit_line"] else ""),
         "credit_line": num(fc["credit_line"])},
        {"id": f"{inn}-outflow", "type": "outflow", "title": t["outflow"].format(date=_date(until, lang)),
         "amount": num(-sum((op["amount"] for op in upcoming), Decimal(0))), "currency": CURRENCY,
         "description": ", ".join(dict.fromkeys(titles[:3])) or t["none"], "date": until},
        {"id": f"{inn}-inflow", "type": "inflow", "title": t["inflow"].format(date=_date(until, lang)),
         "amount": num(fc["daily_inflow"] * (until - today).days), "currency": CURRENCY,
         "description": t["acquiring"] if retail else t["customers"], "date": until},
    ])
