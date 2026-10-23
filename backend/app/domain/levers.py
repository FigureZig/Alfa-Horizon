"""K3 — путь к одобрению (docs/03, docs/12 §8): что клиент реально может изменить и что это даст.

Два уровня. Факторы карты: до какого значения подтянуть фактор, чтобы попасть в лучший интервал, и сколько это баллов.
Контрфакты решения: рычаги — меньше сумма, дольше срок, поручитель, погасить недоимку, снизить долговую нагрузку,
перевести обороты в банк, подождать — по одному и парами через тот же движок в режиме simulate; оставляем только
улучшающие исход, ранжируем по исходу, сумме, ставке и «цене» рычага для клиента. Неустранимое — честно: изменить нельзя.
"""

from decimal import Decimal
from itertools import combinations

from .scoring import _points, score

RANK = {"REJECT": 0, "MANUAL_REVIEW": 1, "REQUEST_INFO": 1, "APPROVE_WITH_CONDITIONS": 2, "COUNTER_OFFER": 2, "APPROVE": 3}
FINAL = {"STOP_LIQUIDATION", "STOP_BANKRUPTCY", "STOP_DELINQUENCY", "POL_INDUSTRY"}
COST = {"wait_requests": 1, "term_up": 2, "amount_down": 3, "move_turnover": 4, "pay_tax_debt": 5, "guarantor": 6,
        "reduce_debt": 7, "wait_age": 8}


def factor_levers(facts: dict, segment: str, card: dict, skip: tuple[str, ...] = ()) -> list[dict]:
    """По каждому фактору: соседний интервал с бо́льшим числом баллов, до какого значения дотянуть, сколько это даст."""
    out = []
    for name, f in card["factors"].items():
        value = None if f.get("source") in skip else facts.get(f["fact"])
        if segment not in f.get("segments", [segment]) or value is None:
            continue
        bins, now = f["bins"], _points(value, f["bins"])
        i = next(k for k, b in enumerate(bins) if _points(value, [b, {"points": None}]) is not None)
        neighbours = [(k, bins[k]) for k in (i - 1, i + 1) if 0 <= k < len(bins) and bins[k]["points"] > now]
        if not neighbours:
            continue
        k, better = max(neighbours, key=lambda kb: kb[1]["points"])
        if k < i:                                           # лучше — меньшие значения: держаться ниже границы
            target, way = better.get("lt", better.get("le")), "below" if "lt" in better else "at_most"
        else:                                               # лучше — большие: дорасти до нижней границы следующего
            target, way = bins[i].get("lt", bins[i].get("le")), "at_least" if "lt" in bins[i] else "above"
        out.append({"factor": name, "reason": f["reason"], "value": value, "points": now, "target": target, "way": way,
                    "gain": better["points"] - now})
    return sorted(out, key=lambda x: -x["gain"])


def _levers(facts: dict, request: dict, decision: dict, pol: dict) -> dict:
    """Применимые рычаги: имя → (как меняет факты, как меняет запрос)."""
    out, product = {}, pol["products"][request["product"]]
    offer = decision.get("offer")
    if facts.get("tax_debt"):
        out["pay_tax_debt"] = ({"tax_debt": Decimal(0)}, {})
    load = facts.get("debt_load")
    if load is not None and load >= 0.15 and facts.get("inflow_avg"):
        target = 0.29 if load >= 0.30 else 0.14
        out["reduce_debt"] = ({"debt_load": target, "debt_payments": Decimal(str(target)) * Decimal(facts["inflow_avg"])}, {})
    share = facts.get("bank_share")
    if share is not None and share < 0.7 and facts.get("inflow_avg"):
        factor = min(Decimal(2), Decimal("0.75") / Decimal(str(max(share, 0.05))))
        inflow = (Decimal(facts["inflow_avg"]) * factor).quantize(Decimal("0.01"))
        out["move_turnover"] = ({"bank_share": 0.75, "inflow_avg": inflow}, {})
    if (facts.get("age_months") or 99) < 12:
        out["wait_age"] = ({"age_months": 12}, {})
    if (facts.get("bki_requests_30d") or 0) > 4:
        out["wait_requests"] = ({"bki_requests_30d": 1}, {})
    if offer and Decimal(str(offer["amount"])) < Decimal(str(request["amount"])) and offer["product"] == request["product"]:
        out["amount_down"] = ({}, {"amount": offer["amount"]})
    if product["repayment"] == "annuity" and (request.get("term_months") or 0) < product["term_months"]["max"]:
        out["term_up"] = ({}, {"term_months": product["term_months"]["max"]})
    security = product["security"].get(facts.get("segment"), product["security"]["default"])
    if not request.get("guarantor") and security != "collateral":
        out["guarantor"] = ({}, {"guarantor": True})
    return out


def _key(d: dict) -> tuple:
    offer = d.get("offer") or {}
    return (RANK[d["outcome"]], Decimal(str(offer.get("amount", 0))), -Decimal(str((offer.get("rate") or {}).get("total", 99))))


def path_to_approval(facts: dict, request: dict, decision: dict, pol: dict, decide, *, limit: int = 3) -> dict:
    """decide — engine.decide (передаётся снаружи, чтобы не было циклического импорта)."""
    codes = {r["code"] for r in decision["reasons"]}
    if codes & FINAL:
        return {"changeable": False, "blocked_by": sorted(codes & FINAL), "options": []}
    levers, base = _levers(facts, request, decision, pol), _key(decision)
    tried = []
    for size in (1, 2):
        for names in combinations(levers, size):
            f, r = dict(facts), dict(request)
            for n in names:
                f.update(levers[n][0])
                r.update(levers[n][1])
            d = decide(f, r, pol, "simulate", allow_alternative=False)
            if _key(d) > base:
                tried.append((names, d))
    if decision["outcome"] == "COUNTER_OFFER":   # путь ко всей сумме — только то, что даёт больше уже предложенного
        current = Decimal(str((decision.get("offer") or {}).get("amount", 0)))
        tried = [(names, d) for names, d in tried if Decimal(str((d.get("offer") or {}).get("amount", 0))) > current]
    best = {}
    for names, d in sorted(tried, key=lambda x: (tuple(-v for v in _key(x[1])), sum(COST[n] for n in x[0]), len(x[0]))):
        if any(set(prev) < set(names) and _key(best[prev]) >= _key(d) for prev in best):
            continue                                        # пара не лучше одиночного рычага из неё — не нужна
        best[names] = d
        if len(best) == limit:
            break
    options = []
    for names, d in best.items():
        offer = d.get("offer") or {}
        options.append({"levers": list(names), "outcome": d["outcome"], "risk_class": (d.get("risk") or {}).get("class"),
                        "score": (d.get("risk") or {}).get("score"), "product": offer.get("product"),
                        "amount": offer.get("amount"), "term_months": offer.get("term_months"),
                        "rate": (offer.get("rate") or {}).get("total")})
    return {"changeable": True, "blocked_by": [], "options": options}


def summary(facts: dict, segment: str, card: dict, skip: tuple[str, ...] = ()) -> dict:
    """Балл с вкладами и рычагами факторов — для «почему так» и кредитного здоровья компании."""
    risk = score(facts, segment, card, skip_sources=skip)
    return {**risk, "base": card["base"], "classes": card["classes"], "levers": factor_levers(facts, segment, card, skip)}
