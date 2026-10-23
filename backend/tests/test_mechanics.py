"""Ядро кредитной механики на «своих персонах» (qa/pairwise.py): инварианты чисел, стоп-факторы, монотонность.

Персоны строятся тем же seed/world.py, что и демо-мир, а ответы источников проходят через JSON, как из WireMock.
Конкретные числа держат golden-сценарии (test_scenarios.py); здесь — правила, которые верны для любой персоны.
"""

import copy
from decimal import Decimal
from itertools import combinations

import pytest

from app.domain import catalog, engine, matching
from qa import invariants, pairwise

from .conftest import TODAY

SETS = {"healthy": pairwise.vectors(pairwise.HEALTHY), "faulty": pairwise.vectors(pairwise.FAULTY),
        "stops": pairwise.stop_vectors()}


@pytest.fixture(scope="module")
def cases(pol) -> dict[str, list[dict]]:
    out, number = {}, 0
    for name, vectors in SETS.items():
        out[name] = [pairwise.build(v, number + i + 1, pol, TODAY) for i, v in enumerate(vectors)]
        number += len(vectors)
    return out


@pytest.mark.parametrize("axes", [pairwise.HEALTHY, pairwise.FAULTY], ids=["healthy", "faulty"])
def test_pairwise_covers_every_pair_of_values(axes):
    vectors = pairwise.vectors(axes)
    for a, b in combinations(axes, 2):
        seen = {(v[a], v[b]) for v in vectors}
        assert seen == {(x, y) for x in axes[a] for y in axes[b]}, (a, b)


@pytest.mark.parametrize("name", list(SETS))
def test_invariants_hold_for_every_persona(cases, pol, name):
    broken = [(c["vector"], errors) for c in cases[name]
              if (errors := invariants.check(c["decision"], c["facts"], c["request"], pol))]
    assert not broken, "\n".join(f"{v}: {e}" for v, e in broken)


def test_stop_factor_rejects_when_visible_and_never_when_unknown(cases):
    for c in cases["stops"]:
        _, code, kind, sources = pairwise.STOPS[c["vector"]["stop"]]
        d, codes = c["decision"], {r["code"] for r in c["decision"]["reasons"]}
        if set(sources) & set(c["sources"]):
            assert (d["outcome"], d["kind"], code in codes) == ("REJECT", kind, True), c["vector"]
        else:
            assert code not in codes and d["outcome"] != "REJECT", c["vector"]   # неизвестно ≠ плохо


def test_simulate_equals_commit_on_complete_data(cases, pol):
    for c in cases["healthy"]:
        simulated = engine.decide(c["facts"], c["request"], pol, "simulate")
        committed = c["decision"]
        assert simulated["outcome"] == committed["outcome"], c["vector"]
        assert (simulated["offer"] or {}).get("amount") == (committed["offer"] or {}).get("amount"), c["vector"]


def test_matching_agrees_with_the_decision_and_explains_every_no(cases, pol):
    """Подбор от задачи = решение по заявке: доступное в подборе так же решит движок, недоступное — всегда с причиной,
    рекомендованный продукт доступен, а стоп-фактор закрывает всё."""
    for c in cases["healthy"] + cases["stops"]:
        req = c["request"]
        found = matching.match(c["facts"], pol, req.get("goal"), req["amount"], req.get("term_months"))
        for option in found["options"]:
            assert option["available"] or option["why"], (c["vector"], option["product"])
            if option["available"] and option["offer"]:          # подбор знает только задачу, сумму и срок
                same = {"product": option["product"], "goal": req.get("goal"),
                        "amount": matching.limit_for(pol["products"][option["product"]], req["amount"]),
                        "term_months": req.get("term_months") or matching.TERMS[option["product"]]}
                again = engine.decide(c["facts"], same, pol, "simulate", allow_alternative=False)
                assert again["outcome"] == option["outcome"], (c["vector"], option["product"])
        if found["recommended"]:
            assert next(o for o in found["options"] if o["product"] == found["recommended"])["available"], c["vector"]
        if found["blockers"]:
            assert not any(o["available"] for o in found["options"]), c["vector"]


def _amount(d: dict, product: str) -> Decimal | None:
    offer = d["offer"]
    return offer["amount"] if offer and offer["product"] == product else None


def test_more_inflows_never_lower_the_limit(cases, pol):
    for c in (c for c in cases["healthy"] if c["decision"]["offer"]):
        product, before = c["decision"]["offer"]["product"], c["decision"]["offer"]["amount"]
        richer_facts = {**c["facts"], "inflow_avg": c["facts"]["inflow_avg"] * Decimal("1.5")}
        richer = engine.decide(richer_facts, c["request"], pol, "commit")
        assert richer["offer"], c["vector"]
        after = _amount(richer, product)
        assert after is None or after >= before, c["vector"]     # None: стал доступен запрошенный продукт


def test_more_debt_never_raises_the_limit(cases, pol):
    for c in (c for c in cases["healthy"] if c["decision"]["offer"]):
        product, before = c["decision"]["offer"]["product"], c["decision"]["offer"]["amount"]
        extra = c["facts"]["inflow_avg"] * Decimal("0.1")
        indebted = engine.decide({**c["facts"], "debt_payments": (c["facts"].get("debt_payments") or 0) + extra},
                                 c["request"], pol, "commit")
        after = _amount(indebted, product)
        assert after is None or after <= before, c["vector"]


def test_price_and_limit_never_reward_risk(pol):
    """Хуже класс — ставка не ниже и множитель лимита не выше; лучше обеспечение — ставка не выше."""
    classes = [c["class"] for c in pol["scorecard"]["classes"]]
    by_lgd = sorted(pol["risk_pricing"]["lgd"], key=lambda s: pol["risk_pricing"]["lgd"][s])
    for section in pol["sections"]:
        for term in (12, 36):
            for security in by_lgd:
                rates = [catalog.rate(pol, section, term, cls, security)["total"] for cls in classes]
                assert rates == sorted(rates), (section, term, security)
            for cls in classes:
                rates = [catalog.rate(pol, section, term, cls, s)["total"] for s in by_lgd]
                assert rates == sorted(rates), (section, term, cls)
    for code, product in pol["products"].items():
        multipliers = [product["class_multiplier"][cls] for cls in classes]
        assert multipliers == sorted(multipliers, reverse=True), code


def test_invariants_catch_a_tampered_decision(cases, pol):
    """Сами инварианты не пустые: испорченное решение они ловят."""
    c = next(c for c in cases["healthy"] if c["decision"]["outcome"] == "APPROVE")
    tampering = {
        "ставка": lambda d: d["offer"]["rate"].update(risk=d["offer"]["rate"]["risk"] + 1),
        "сумма": lambda d: d["offer"].update(amount=d["offer"]["amount"] * 50),
        "статус": lambda d: d.update(status="REJECTED"),
        "стоп": lambda d: d["reasons"].append({"code": "STOP_BANKRUPTCY", "kind": "stop", "text": ""}),
    }
    for what, tamper in tampering.items():
        d = copy.deepcopy(c["decision"])
        tamper(d)
        assert invariants.check(d, c["facts"], c["request"], pol), what
