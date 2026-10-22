"""Решение по заявке (docs/04, docs/13).

Порядок: стоп-факторы → продукт подходит отрасли → требования (крупная сделка, расхождения) → скоринг →
ставка и лимит с контрпредложением → полномочия → исход по приоритету.
Чистая функция: те же факты и та же политика дают тот же результат.
mode: "simulate" — предодобрение и «что если»; "commit" — решение по поданной заявке (с политиками фактов).
"""

from decimal import Decimal

from . import catalog as cat
from .calc import dec, money, payment
from .scoring import score
from .state import OUTCOME_STATUS

OFFER_KIND = {"APPROVE": "AS_REQUESTED", "COUNTER_OFFER": "COUNTER", "APPROVE_WITH_CONDITIONS": "CONDITIONAL"}
PREAPPROVAL_LABEL = {"APPROVE": "PREAPPROVED", "COUNTER_OFFER": "PREAPPROVED", "APPROVE_WITH_CONDITIONS": "CONDITIONAL",
                     "REQUEST_INFO": "REVIEW", "MANUAL_REVIEW": "REVIEW", "REJECT": "UNAVAILABLE"}
REJECT_REASON_KINDS = {"stop", "policy", "score", "cap"}     # в отказе — только то, что его объясняет
CAP_ASK = {"CAP_COLLATERAL": "REQ_COLLATERAL_VALUE", "CAP_TURNOVER": "REQ_TURNOVER_DATA",
           "CAP_PAYMENT_CAPACITY": "REQ_TURNOVER_DATA", "CAP_INTEREST_CAPACITY": "REQ_TURNOVER_DATA",
           "CAP_SEASONAL_INFLOWS": "REQ_TURNOVER_DATA"}


def _fmt(value):
    if isinstance(value, (int, Decimal)) and not isinstance(value, bool) and value == int(value) and abs(value) >= 1000:
        return f"{int(value):,}".replace(",", " ")
    return value


class _Log:
    """Причины — для клиента и досье; трасса — для «почему так» и аудита."""

    def __init__(self, pol: dict):
        self.pol, self.reasons, self.trace = pol, [], []

    def reason(self, code: str, kind: str, **ctx) -> None:
        values = {k: _fmt(v) for k, v in {**self.pol["params"], **ctx}.items()}
        template = self.pol["reasons"].get(code, code)
        try:
            text = template.format(**values)
        except (KeyError, IndexError, ValueError):
            text = template
        self.reasons.append({"code": code, "kind": kind, "text": text})

    def step(self, name: str, **data) -> None:
        self.trace.append({"step": name, **data})


def decide(facts: dict, request: dict, pol: dict, mode: str = "simulate", *, allow_alternative: bool = True) -> dict:
    log = _Log(pol)
    params, code = pol["params"], request["product"]
    product = pol["products"][code]
    amount = dec(request["amount"])
    term = _clamp_term(request.get("term_months"), product)
    segment, section = facts.get("segment"), facts.get("section")
    res = {"log": log, "pol": pol, "mode": mode, "request": {**request, "term_months": term}}

    stops = _stops(facts, params, pol, log)
    if stops:
        return _result("REJECT", **res, kind=_reject_kind(stops), hints=_hints(pol, section))
    if segment is None or section is None:          # реестр не ответил: ЕГРЮЛ/ЕГРИП — WAIT → дедлайн → MANUAL (docs/07 §4)
        log.reason("DATA_SOURCE_UNAVAILABLE", "manual", source="ЕГРЮЛ/ЕГРИП")
        return _result("MANUAL_REVIEW", **res, flags=["SOURCE_WAIT"] if mode == "commit" else [])

    misfit = _misfit(code, facts, pol, amount)
    if misfit:
        log.reason(misfit, "policy", product_name=product["name"], months=product.get("requires", {}).get("turnover_months"),
                   min=product["amount"]["min"])
        alt = _alternative(facts, request, pol, mode) if allow_alternative else None
        if alt:
            return _product_counter(alt, log, res["request"])
        return _result("REJECT", **res, kind="POLICY", hints=_hints(pol, section))

    asks, manual, flags, conditions = [], [], [], []
    for what in facts.get("conflicts", []):
        manual.append("DATA_CONFLICT")
        log.reason("DATA_CONFLICT", "manual", what=what)
    if pol["sections"][section].get("manual"):
        manual.append("POL_INDUSTRY_REVIEW")
        log.reason("POL_INDUSTRY_REVIEW", "manual")

    # БКИ неизвестно → факторы БКИ = 0 (docs/12 §3); в заявке — политика факта PROVISIONAL или MANUAL (docs/07 §4)
    bki_known = bool(facts.get("bki_known"))
    unknown = () if bki_known else ("bki",) if facts.get("bki_info_known") else ("bki", "bki_info")
    risk = score(facts, segment, pol["scorecard"], skip_sources=unknown)
    log.step("scoring", score=risk["score"], risk_class=risk["class"], best_class=risk["best_class"], missing=risk["missing"])

    class_policy = product["class_policy"][risk["class"]]
    if class_policy == "reject" and product["class_policy"][risk["best_class"]] != "reject":
        class_policy = "wait"                       # отказ держится только на неизвестной КИ — неизвестно ≠ плохо (docs/07 §1)
    provisional = False
    if not bki_known and mode == "commit":
        if amount <= dec(params["provisional_max"]) and class_policy != "wait":
            provisional = True                      # флаг ставим, только если дойдёт до оферты
        else:
            flags.append("SOURCE_WAIT")
            manual.append("DATA_SOURCE_UNAVAILABLE")
            log.reason("DATA_SOURCE_UNAVAILABLE", "manual", source="БКИ")
    elif class_policy == "wait":
        manual.append("BKI_NEEDED")
        log.reason("BKI_NEEDED", "manual")

    if class_policy == "reject":
        log.reason("POL_RISK_CLASS", "policy")
        for weak in risk["weak"]:
            log.reason(weak, "score")
        return _result("REJECT", **res, kind="POLICY", risk=risk, hints=_hints(pol, section))
    if class_policy == "manual":
        manual.append("POL_PRODUCT_REVIEW")
        log.reason("POL_PRODUCT_REVIEW", "manual")
    if class_policy == "wait" or (class_policy == "manual" and not dec(product["class_multiplier"][risk["class"]])):
        # авто-оферты нет: ждём КИ или класс без авто-лимита (D, docs/12 §5–6) — сумму и документы определит специалист
        log.step("outcome", outcome="MANUAL_REVIEW", manual=manual)
        return _result("MANUAL_REVIEW", **res, risk=risk, flags=flags)
    security = cat.security_for(product, segment)
    if request.get("guarantor") and security != "collateral":    # клиент сразу привёл поручителя (ГК ст. 361)
        security = "guarantor"
    elif class_policy == "conditional":
        security = "guarantor"
        conditions.append("GUARANTEE")
        log.reason("REQ_GUARANTOR", "condition")

    quote = _quote(product, facts, term, risk["class"], security, section, pol, request)
    for cap in quote["caps"]:
        ask = CAP_ASK.get(cap["code"]) if cap["value"] is None else None
        if ask and ask not in asks:
            asks.append(ask)
            log.reason(ask, "ask")
    if quote["limit"] is None:
        return _result("REQUEST_INFO" if asks else "REJECT", **res, kind=None if asks else "POLICY",
                       risk=risk, asks=asks, caps=quote["caps"])

    offer, alternatives, counter = _offer(code, product, facts, amount, term, risk["class"], security, section, pol,
                                          request, quote, log)
    if offer is None:
        log.reason("POL_AMOUNT_MIN", "policy", min=product["amount"]["min"])
        alt = _alternative(facts, request, pol, mode) if allow_alternative else None
        if alt:
            return _product_counter(alt, log, res["request"])
        return _result("REJECT", **res, kind="POLICY", risk=risk, caps=quote["caps"], hints=_hints(pol, section))

    if _needs_corporate_approval(facts, offer["amount"], params, request, log):   # крупность — по самой сделке
        asks.insert(0, "REQ_CORP_APPROVAL")
    if offer["amount"] > dec(params["auto_authority_max"]):
        manual.append("POL_AUTHORITY_EXCEEDED")
        log.reason("POL_AUTHORITY_EXCEEDED", "manual")
    if provisional:
        flags.append("PROVISIONAL")
        log.reason("PROVISIONAL", "flag")

    if asks:
        outcome = "REQUEST_INFO"
    elif manual:
        outcome = "MANUAL_REVIEW"
    elif conditions:
        outcome = "APPROVE_WITH_CONDITIONS"
    elif counter:
        outcome = "COUNTER_OFFER"
    else:
        outcome = "APPROVE"
    log.step("outcome", outcome=outcome, asks=asks, manual=manual, conditions=conditions, counter=counter)
    return _result(outcome, **res, risk=risk, offer=offer, alternatives=alternatives, counter=counter,
                   conditions=conditions, asks=asks, flags=flags, caps=quote["caps"])


def stop_factors(facts: dict, pol: dict) -> list[dict]:
    """Стоп-факторы на текущих фактах — финальная проверка перед выдачей (ГК ст. 821 п. 1, docs/07 N6, N17)."""
    log = _Log(pol)
    _stops(facts, pol["params"], pol, log)
    return log.reasons


def manual_terms(code: str, amount, term_months, facts: dict, pol: dict, risk_class: str | None = None) -> dict:
    """Условия, которые ставит специалист (сумма и срок — его решение), по той же цене риска: КС + отрасль + риск."""
    product = pol["products"][code]
    term = _clamp_term(term_months, product)
    risk_class = risk_class or score(facts, facts.get("segment"), pol["scorecard"])["class"]
    quote = {"term": term, "rate": cat.rate(pol, facts.get("section"), term, risk_class,
                                           cat.security_for(product, facts.get("segment"))), "binding": None}
    return _terms(code, product, dec(amount), quote)


def preapprove(facts: dict, pol: dict, goal: str, amount, term_months: int | None = None) -> list[dict]:
    """Подбор (U2): продукты цели в отрасли клиента с меткой предодобрено / условно / рассмотрение / недоступно."""
    out = []
    for code in pol["goals"][goal]["products"]:
        req = {"product": code, "amount": amount, "term_months": term_months, "goal": goal}
        d = decide(facts, req, pol, "simulate", allow_alternative=False)
        out.append({"product": code, "name": pol["products"][code]["name"], "label": PREAPPROVAL_LABEL[d["outcome"]],
                    "decision": d})
    return out


# ── шаги ─────────────────────────────────────────────────────────────────────────────────────────────────────────


def _clamp_term(term, product: dict) -> int:
    bounds = product["term_months"]
    return min(max(int(term or bounds["max"]), bounds["min"]), bounds["max"])


def _stops(facts: dict, params: dict, pol: dict, log: _Log) -> list[tuple[str, bool]]:
    """Стоп-факторы до скоринга (docs/12 §2): (код, устранимо ли)."""
    found: list[tuple[str, bool]] = []

    def stop(code: str, fixable: bool, **ctx) -> None:
        found.append((code, fixable))
        log.reason(code, "stop", **ctx)

    if facts.get("liquidation"):
        stop("STOP_LIQUIDATION", False)
    if facts.get("bankruptcy"):
        stop("STOP_BANKRUPTCY", False)
    for person in facts.get("eio", []):
        if person.get("disqualified"):
            stop("STOP_EIO_DISQUALIFIED", True)
        if person.get("unreliable"):
            stop("STOP_EIO_UNRELIABLE", True)
    tax_debt = facts.get("tax_debt")
    if tax_debt is not None and tax_debt > params["tax_debt_max"]:
        stop("STOP_TAX_DEBT", True, tax_debt=tax_debt)
    if (facts.get("max_overdue_days") or 0) > params["overdue_stop_days"]:
        stop("STOP_DELINQUENCY", False)
    age = facts.get("age_months")
    if age is not None and age < params["min_business_age_months"]:
        stop("POL_BUSINESS_AGE", True)
    if facts.get("okved"):                          # без ответа реестра отрасль неизвестна — это не отказ
        ok, why = cat.section_check(pol, facts["okved"], facts.get("section"))
        if not ok:
            stop("POL_INDUSTRY", False, okved=facts["okved"], why=why)
    log.step("stops", found=[code for code, _ in found])
    return found


def _reject_kind(stops: list[tuple[str, bool]]) -> str:
    if all(code.startswith("POL_") for code, _ in stops):
        return "POLICY"
    return "STOP_FIXABLE" if all(fixable for _, fixable in stops) else "STOP_FINAL"


def _misfit(code: str, facts: dict, pol: dict, amount: Decimal) -> str | None:
    """Продукт не предлагается этой отрасли или сегменту, сумма меньше минимальной, либо нет нужных данных."""
    if code not in cat.available_products(pol, facts.get("section"), facts.get("segment")):
        return "POL_PRODUCT_FIT"
    if amount < dec(pol["products"][code]["amount"]["min"]):
        return "POL_AMOUNT_RANGE"
    requires = pol["products"][code].get("requires", {})
    if requires.get("turnover_months") and (facts.get("turnover_months") or 0) < requires["turnover_months"]:
        return "POL_NO_TURNOVER"
    if requires.get("eis_contract") and not facts.get("contracts"):
        return "POL_NO_CONTRACT"
    return None


def _alternative(facts: dict, request: dict, pol: dict, mode: str) -> dict | None:
    """Другой продукт под ту же цель клиента → контрпредложение PRODUCT (docs/04 §8 п. 5)."""
    goal = request.get("goal")
    for code in pol["goals"].get(goal, {}).get("products", []):
        if code == request["product"] or _misfit(code, facts, pol, dec(request["amount"])):
            continue
        d = decide(facts, {**request, "product": code}, pol, mode, allow_alternative=False)
        if d["outcome"] != "REJECT":
            return d
    return None


def _product_counter(alt: dict, log: _Log, request: dict) -> dict:
    alt["request"] = _request_view(request)          # в решении — то, что просил клиент, а не подобранный продукт
    why_not = [r for r in log.reasons if r["kind"] in REJECT_REASON_KINDS]   # почему не тот продукт; условия — от нового
    alt["reasons"] = why_not + alt["reasons"]
    alt["trace"] = log.trace + alt["trace"]
    alt["counter"] = ["PRODUCT", *[c for c in alt["counter"] if c != "PRODUCT"]]
    if alt["outcome"] in ("APPROVE", "COUNTER_OFFER"):
        alt["outcome"], alt["offer_kind"], alt["status"] = "COUNTER_OFFER", "COUNTER", OUTCOME_STATUS["COUNTER_OFFER"]
    return alt


def _needs_corporate_approval(facts: dict, amount: Decimal, params: dict, request: dict, log: _Log) -> bool:
    """Крупная сделка ≥ 25% активов: согласие участников (14-ФЗ ст. 46) или акционеров (208-ФЗ ст. 78–79)."""
    if facts.get("segment") not in ("LLC", "JSC"):
        return False
    assets = facts.get("assets")
    share = amount / dec(assets) if assets else None
    if share is not None and share < dec(params["large_deal_share"]):
        log.step("large_deal", share=str(round(share, 3)), result=False)
        return False
    participants, eio = facts.get("participants", []), facts.get("eio", [])
    sole = (facts["segment"] == "LLC" and len(participants) == 1 and len(eio) == 1
            and participants[0].get("inn") == eio[0].get("inn"))          # 14-ФЗ ст. 46 п. 7
    approved = bool(request.get("corporate_approval"))
    log.step("large_deal", share=None if share is None else str(round(share, 3)), assumed_large=share is None,
             sole_owner_is_eio=sole, approval=approved, norm="14-ФЗ ст. 46 п. 1, 3, 7; 208-ФЗ ст. 78–79")
    if sole or approved:
        return False
    log.reason("REQ_CORP_APPROVAL", "ask", share_pct="≥ 25" if share is None else int(share * 100))
    return True


def _quote(product: dict, facts: dict, term: int, risk_class: str, security: str, section, pol: dict, request: dict) -> dict:
    r = cat.rate(pol, section, term, risk_class, security)
    caps = cat.caps(product, facts, term, r["total"], pol, request.get("collateral_value"))
    lim, binding = cat.limit(product, caps, risk_class, pol["params"])
    return {"term": term, "rate": r, "caps": caps, "limit": lim, "binding": binding}


def _terms(code: str, product: dict, amount: Decimal, quote: dict) -> dict:
    r = quote["rate"]
    return {"product": code, "product_name": product["name"], "amount": money(amount), "term_months": quote["term"],
            "repayment": product["repayment"], "rate": r,
            "payment": payment(product["repayment"], amount, r["total"], quote["term"]),
            "binding_cap": quote["binding"]}


def _offer(code, product, facts, amount, term, risk_class, security, section, pol, request, quote, log):
    """Основной вариант и альтернатива внутри политики (docs/04 §8): полная сумма на больший срок, иначе меньше сумма."""
    if quote["limit"] >= amount:
        return _terms(code, product, amount, quote), [], []
    minimum = dec(product["amount"]["min"])
    same_term = _terms(code, product, quote["limit"], quote) if quote["limit"] >= minimum else None
    longer, longer_counter = None, None
    if product["repayment"] == "annuity":
        t, t_max, step = term, product["term_months"]["max"], pol["params"]["term_search_step_months"]
        while t < t_max:
            t = min(t + step, t_max)
            q = _quote(product, facts, t, risk_class, security, section, pol, request)
            if q["limit"] is None:
                break
            if q["limit"] >= amount:
                longer, longer_counter = _terms(code, product, amount, q), ["TERM"]
                break
            if q["limit"] > quote["limit"] and q["limit"] >= minimum:
                longer, longer_counter = _terms(code, product, q["limit"], q), ["AMOUNT", "TERM"]
    log.reason(quote["binding"], "cap")
    log.step("counter_search", requested=str(amount), limit=str(quote["limit"]), binding=quote["binding"])
    if longer_counter == ["TERM"]:
        return longer, [same_term] if same_term else [], ["TERM"]
    if same_term:
        return same_term, [longer] if longer else [], ["AMOUNT"]
    if longer:
        return longer, [], longer_counter
    return None, [], []


def _hints(pol: dict, section) -> list[str]:
    keys = (pol["sections"].get(section) or {}).get("alternatives", [])
    return [pol["alternatives"][k] for k in keys]


def _request_view(request: dict) -> dict:
    return {"product": request["product"], "amount": money(request["amount"]), "term_months": request.get("term_months"),
            "goal": request.get("goal")}


def _result(outcome: str, *, log: _Log, pol: dict, mode: str, request: dict, kind=None, risk=None, offer=None,
            alternatives=(), counter=(), conditions=(), asks=(), flags=(), caps=None, hints=()) -> dict:
    return {
        "mode": mode,
        "policy_version": pol["version"],
        "outcome": outcome,
        "kind": kind,                                   # REJECT: STOP_FIXABLE · STOP_FINAL · POLICY
        "status": OUTCOME_STATUS[outcome],
        "offer_kind": OFFER_KIND.get(outcome),
        "counter": list(counter),                       # PRODUCT · TERM · AMOUNT
        "conditions": list(conditions),                 # GUARANTEE · COLLATERAL
        "asks": list(asks),
        "flags": list(flags),
        "request": _request_view(request),
        "offer": offer,
        "alternatives": [a for a in alternatives if a],
        "caps": caps,
        "risk": risk,
        "hints": list(hints),                           # некредитные альтернативы (лизинг, факторинг, гарантия)
        "reasons": [r for r in log.reasons if outcome != "REJECT" or r["kind"] in REJECT_REASON_KINDS],
        "trace": log.trace,
    }
