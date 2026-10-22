"""Инварианты решения: что должно быть верно для любой персоны, любого запроса и любого сбоя.

Не сверяют конкретные числа (их держат golden-сценарии), а проверяют, что числа адекватны: ставка собрана
из частей по правилам, сумма и срок в границах продукта, платёж посчитан верно, кредит по карману компании,
стоп-фактор всегда даёт отказ, неизвестное не превращается ни в «да», ни в «нет».
"""

from decimal import Decimal

from app.domain import catalog
from app.domain.calc import dec, payment
from app.domain.state import OUTCOME_STATUS

OFFER_OUTCOMES = {"APPROVE", "COUNTER_OFFER", "APPROVE_WITH_CONDITIONS"}
FINAL_STOPS = {"STOP_LIQUIDATION", "STOP_BANKRUPTCY", "STOP_DELINQUENCY"}
OUTCOME_REASON = {"REQUEST_INFO": "ask", "MANUAL_REVIEW": "manual", "APPROVE_WITH_CONDITIONS": "condition"}
TOLERANCE = Decimal("1.00")                     # рубль на округление копеек в обратной задаче платежа

INVARIANTS = [   # для отчёта: что проверяется на каждом векторе
    "статус заявки соответствует исходу; у всего, кроме APPROVE, есть причина; у дозапроса, ручной проверки "
    "и условного одобрения — причина своего вида",
    "одобрение всегда с офертой, отказ — без оферты и с видом отказа; в причинах отказа только то, что его объясняет",
    "стоп-фактор → отказ; ликвидация, банкротство, просрочка > 90 дн. → окончательный отказ",
    "реестр не ответил → только ручная проверка или отказ по стоп-фактору из других источников",
    "заявка без КИ → оферта только предварительная и не больше provisional_max; флаг «предварительно» — только при оферте",
    "ставка = КС + отраслевой спред раздела ОКВЭД + спред за риск класса; КС из политики; итог в коридоре",
    "сумма и срок в границах продукта; сумма контрпредложения кратна шагу округления",
    "платёж совпадает с калькулятором; все платежи по кредитам ≤ 30% поступлений; овердрафт ≤ 40% поступлений",
    "залог, контракт, сезонность ограничивают сумму по своим долям",
    "APPROVE = ровно запрошенное; контрпредложение отличается от запроса; авторешение не выше порога полномочий",
    "предлагаем только продукт, доступный отрасли и форме бизнеса; согласие на крупную сделку — по сумме оферты",
    "балл в шкале карты, класс по порогам",
]


def check(d: dict, facts: dict, request: dict, pol: dict) -> list[str]:
    """Пустой список — решение адекватно. Иначе — что нарушено."""
    params, out = pol["params"], []
    bad = out.append
    outcome, offer = d["outcome"], d["offer"]
    kinds = {r["kind"] for r in d["reasons"]}
    codes = {r["code"] for r in d["reasons"]}

    if d["status"] != OUTCOME_STATUS[outcome]:
        bad(f"статус {d['status']} не соответствует исходу {outcome}")
    if outcome != "APPROVE" and not d["reasons"]:
        bad("исход без причины")
    if outcome in OUTCOME_REASON and OUTCOME_REASON[outcome] not in kinds:
        bad(f"{outcome} без причины вида {OUTCOME_REASON[outcome]}")
    if outcome in OFFER_OUTCOMES and not offer:
        bad("одобрение без оферты")
    if outcome == "REJECT":
        if offer:
            bad("отказ с офертой")
        if d["kind"] not in ("STOP_FIXABLE", "STOP_FINAL", "POLICY"):
            bad("отказ без вида")
        if kinds - {"stop", "policy", "score", "cap"}:
            bad(f"в причинах отказа лишнее: {sorted(kinds - {'stop', 'policy', 'score', 'cap'})}")
        if codes & FINAL_STOPS and d["kind"] != "STOP_FINAL":
            bad("необратимый стоп-фактор, а отказ не окончательный")
    if "stop" in kinds and outcome != "REJECT":
        bad("стоп-фактор без отказа")

    if facts.get("liquidation") or facts.get("bankruptcy") or (facts.get("max_overdue_days") or 0) > params["overdue_stop_days"]:
        if outcome != "REJECT":
            bad("известный необратимый стоп-фактор без отказа")
    tax_debt = facts.get("tax_debt")
    if tax_debt is not None and tax_debt > params["tax_debt_max"] and outcome != "REJECT":
        bad("недоимка выше порога без отказа")
    if facts.get("segment") is None and outcome not in ("MANUAL_REVIEW", "REJECT"):
        bad("реестр не ответил, а решение автоматическое")
    if facts.get("segment") is None and outcome == "REJECT" and "stop" not in kinds:
        bad("реестр не ответил, а отказ не по стоп-фактору")
    if "REQ_CORP_APPROVAL" in d["asks"]:
        assets = facts.get("assets")
        if not offer:
            bad("согласие на крупную сделку без оферты")
        elif assets and offer["amount"] < dec(params["large_deal_share"]) * dec(assets):
            bad("согласие на крупную сделку, а оферта меньше порога от активов")
    if "PROVISIONAL" in d["flags"] and not offer:
        bad("«условия предварительные» без оферты")
    if d["mode"] == "commit" and not facts.get("bki_known") and outcome in OFFER_OUTCOMES:
        if "PROVISIONAL" not in d["flags"]:
            bad("без КИ оферта не помечена предварительной")
        if offer["amount"] > dec(params["provisional_max"]):
            bad("предварительная оферта выше provisional_max")

    if outcome in OFFER_OUTCOMES and offer:
        asked = d["request"]
        if outcome == "APPROVE" and (offer["product"], offer["amount"]) != (asked["product"], asked["amount"]):
            bad("APPROVE не равен запросу")
        if outcome == "COUNTER_OFFER":
            if not d["counter"]:
                bad("контрпредложение без вида")
            same = ("product", "amount", "term_months")
            if [offer[k] for k in same] == [asked[k] for k in same]:
                bad("контрпредложение совпадает с запросом")
        if offer["amount"] > dec(params["auto_authority_max"]):
            bad("авторешение выше порога полномочий")
    for o in ([offer] if offer else []) + list(d["alternatives"]):
        out += [f"{o['product']} {o['amount']}: {v}" for v in offer_violations(o, d, facts, request, pol)]

    if risk := d["risk"]:
        card = pol["scorecard"]
        if not card["min"] <= risk["score"] <= card["max"]:
            bad(f"балл {risk['score']} вне шкалы")
        if risk["class"] != next(c["class"] for c in card["classes"] if risk["score"] >= c["min"]):
            bad("класс не по порогам")
    return out


def offer_violations(o: dict, d: dict, facts: dict, request: dict, pol: dict) -> list[str]:
    params, out = pol["params"], []
    bad = out.append
    product, r = pol["products"][o["product"]], o["rate"]
    bucket = catalog.term_bucket(o["term_months"], params)
    if o["product"] not in catalog.available_products(pol, facts.get("section"), facts.get("segment")):
        bad("продукта нет для этой отрасли или формы бизнеса")

    if r["total"] != r["key_rate"] + r["industry"] + r["risk"]:
        bad("ставка не равна сумме частей")
    if r["key_rate"] != dec(pol["market"]["key_rate"]["value"]):
        bad("КС не из политики")
    if r["bucket"] != bucket or r["industry"] != catalog.industry_spread(pol["market"], facts.get("section"), bucket):
        bad("отраслевой спред не по разделу ОКВЭД и сроку")
    if d["risk"] and (r["risk_class"] != d["risk"]["class"]
                      or r["risk"] != catalog.risk_spread(pol["risk_pricing"], d["risk"]["class"], r["security"])):
        bad("спред за риск не по классу и обеспечению")
    worst = max(catalog.risk_spread(pol["risk_pricing"], "D", s) for s in pol["risk_pricing"]["lgd"])
    if not r["key_rate"] <= r["total"] <= r["key_rate"] + catalog.industry_spread(pol["market"], None, "short") + worst:
        bad(f"ставка {r['total']} вне коридора")

    lo, hi = dec(product["amount"]["min"]), dec(product["amount"]["max"])
    if not lo <= o["amount"] <= hi:
        bad(f"сумма вне границ продукта {lo}–{hi}")
    if not product["term_months"]["min"] <= o["term_months"] <= product["term_months"]["max"]:
        bad("срок вне границ продукта")
    if o["amount"] != d["request"]["amount"]:
        step = params["amount_step_small"] if o["amount"] < 1_000_000 else params["amount_step_large"]
        if o["amount"] % step:
            bad(f"сумма не кратна шагу {step}")
    if o["payment"] != payment(product["repayment"], o["amount"], r["total"], o["term_months"]):
        bad("платёж не совпадает с калькулятором")

    inflow, debts = facts.get("inflow_avg"), dec(facts.get("debt_payments") or 0)
    if inflow:
        room = dec(params["p_payment"]) * dec(inflow) + TOLERANCE
        if product["repayment"] == "revolving" and o["amount"] > dec(params["k_overdraft"]) * dec(inflow) + TOLERANCE:
            bad("овердрафт больше 40% поступлений")
        if product["repayment"] in ("annuity", "bullet") and debts + o["payment"] > room:
            bad(f"платежи {debts + o['payment']} больше 30% поступлений")
        if "SEASONAL_INFLOWS" in product["caps"] and o["amount"] > dec(product["seasonal_share"]) * dec(inflow) * 12:
            bad("сезонный кредит больше доли годовых поступлений")
    if "COLLATERAL" in product["caps"] and request.get("collateral_value") and o["product"] == request["product"]:
        if o["amount"] > dec(product["ltv_max"]) * dec(request["collateral_value"]):
            bad("сумма больше доли залога")
    if "CONTRACT" in product["caps"]:
        cap = catalog.contract_cap(facts.get("contracts"), product)
        if cap is None or o["amount"] > cap:
            bad("сумма больше доли контракта или контракта нет")
    return out
