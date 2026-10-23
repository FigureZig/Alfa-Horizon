"""Подбор от задачи (U2, JTBD — docs/02): клиент говорит, на что нужны деньги, а банк по своим данным показывает, какие
продукты этой компании доступны, сколько дадут, под какую ставку и что для этого понадобится. Недоступное — с причиной.

Чистая функция поверх движка решения: те же факты и политика, что и у заявки, — подбор и решение не расходятся.
"""

from decimal import Decimal

from . import catalog
from .calc import dec
from .engine import PREAPPROVAL_LABEL, decide, stop_factors

TERMS = {"OVERDRAFT": 12, "EXPRESS": 36, "WORKING_CAPITAL": 24, "INVESTMENT": 60, "CONTRACT": 12, "AGRO_SEASONAL": 10}


def _needs(d: dict, facts: dict) -> list[str]:
    """Что понадобится, кроме подачи заявки."""
    needs = ["consent_bki"] * (not facts.get("bki_known"))
    needs += ["corporate_approval"] * ("REQ_CORP_APPROVAL" in d["asks"])
    needs += ["collateral"] * ("REQ_COLLATERAL_VALUE" in d["asks"] or "COLLATERAL" in d["conditions"])
    needs += ["guarantor"] * ("GUARANTEE" in d["conditions"])
    needs += ["specialist"] * (d["outcome"] == "MANUAL_REVIEW")
    return list(dict.fromkeys(needs))


def limit_for(product: dict, need) -> Decimal:
    """Сколько просить: у овердрафта сумма — лимит, из него берут сколько нужно, поэтому не меньше минимума продукта."""
    need = dec(need)
    return max(need, dec(product["amount"]["min"])) if product["repayment"] == "revolving" else need


def _terms(offer: dict | None) -> dict | None:
    if not offer:
        return None
    return {"amount": offer["amount"], "term_months": offer["term_months"], "rate": offer["rate"]["total"],
            "payment": offer["payment"], "repayment": offer["repayment"]}


def match(facts: dict, pol: dict, goal: str | None = None, amount=None, term_months: int | None = None) -> dict:
    """→ {blockers, options[], recommended}. amount — сколько нужно клиенту (нет — максимум продукта),
    term_months — на сколько (нет — типичный срок продукта)."""
    blockers = stop_factors(facts, pol)
    codes = pol["goals"][goal]["products"] if goal else list(pol["products"])
    fit = set(catalog.available_products(pol, facts.get("section"), facts.get("segment")))
    options = []
    for code in codes:
        product = pol["products"][code]
        term = term_months or TERMS[code]
        base = {"product": code, "name": product["name"], "repayment": product["repayment"]}
        if code not in fit:
            text = pol["reasons"]["POL_PRODUCT_FIT"].format(product_name=product["name"])
            options.append({**base, "available": False, "label": "UNAVAILABLE", "outcome": "REJECT", "max_amount": None,
                            "offer": None, "counter": [], "needs": [], "why": [text],
                            "causes": [{"code": "POL_PRODUCT_FIT", "kind": "policy", "text": text}]})
            continue
        most = decide(facts, {"product": code, "amount": product["amount"]["max"], "term_months": term, "goal": goal}, pol,
                      "simulate", allow_alternative=False)
        want = most if amount is None else decide(facts, {"product": code, "amount": limit_for(product, amount),
                                                          "term_months": term, "goal": goal},
                                                  pol, "simulate", allow_alternative=False)
        causes = [{"code": r["code"], "kind": r["kind"], "text": r["text"]} for r in want["reasons"]
                  if r["kind"] in ("stop", "policy", "cap", "score", "manual")]
        options.append({**base, "available": want["outcome"] != "REJECT", "label": PREAPPROVAL_LABEL[want["outcome"]],
                        "outcome": want["outcome"], "max_amount": (most["offer"] or {}).get("amount"),
                        "offer": _terms(want["offer"]), "counter": want["counter"], "needs": _needs(want, facts),
                        "why": [c["text"] for c in causes], "causes": causes})
    return {"blockers": blockers, "options": options, "recommended": _best(options, amount)}


READY = {"PREAPPROVED": 0, "CONDITIONAL": 1}   # решает сам банк: сразу или с условием (поручитель, залог)


def _best(options: list[dict], amount) -> str | None:
    """Что посоветовать под задачу: то, что закрывает нужную сумму, — сначала без условий, потом с условиями, дешевле;
    если всю сумму не закрывает никто — то, что даёт больше всего (овердрафт на 5% нужды не совет).
    Без суммы — предодобренное с самым большим лимитом."""
    ready = [o for o in options if o["available"] and o["label"] in READY and o["offer"]]
    if amount is not None:
        enough = [o for o in ready if dec(o["offer"]["amount"]) >= dec(amount)]
        if enough:
            return min(enough, key=lambda o: (READY[o["label"]], dec(o["offer"]["rate"])))["product"]
        if ready:
            return max(ready, key=lambda o: (dec(o["offer"]["amount"]), -READY[o["label"]]))["product"]
        return None
    pre = [o for o in ready if o["label"] == "PREAPPROVED"]
    return max(pre, key=lambda o: dec(o["max_amount"] or Decimal(0)))["product"] if pre else None
