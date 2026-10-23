"""K3 — путь к одобрению: рычаги всегда улучшают решение, неустранимое честно неустранимо, цели факторов достижимы."""

from datetime import date
from decimal import Decimal

import pytest

from app.domain import engine, levers
from app.domain.scoring import _points
from qa import pairwise

from .conftest import COMPANIES, facts_of

TODAY = date(2026, 10, 21)


def test_tax_arrears_decline_turns_into_approval(pol):
    romashka = COMPANIES["7701000033"]
    facts, request = facts_of(romashka["inn"]), romashka["scenario"]["request"]
    decision = engine.decide(facts, request, pol, "commit")
    path = levers.path_to_approval(facts, request, decision, pol, engine.decide)
    assert decision["outcome"] == "REJECT"
    assert path["options"][0]["levers"] == ["pay_tax_debt"] and path["options"][0]["outcome"] == "APPROVE"


def _key(outcome: str, amount, rate) -> tuple:
    return levers.RANK[outcome], Decimal(str(amount or 0)), -Decimal(str(rate if rate is not None else 99))


@pytest.fixture(scope="module")
def cases(pol):
    vectors = pairwise.vectors(pairwise.HEALTHY)[:24] + pairwise.stop_vectors()[:24]
    return [pairwise.build(v, 700 + i, pol, TODAY) for i, v in enumerate(vectors)]


def test_every_option_improves_and_final_stops_have_none(cases, pol):
    for c in cases:
        d = c["decision"]
        path = levers.path_to_approval(c["facts"], c["request"], d, pol, engine.decide)
        if {r["code"] for r in d["reasons"]} & levers.FINAL:
            assert not path["changeable"] and not path["options"], c["vector"]
            continue
        offer = d["offer"] or {}
        base = _key(d["outcome"], offer.get("amount"), (offer.get("rate") or {}).get("total"))
        for option in path["options"]:
            assert _key(option["outcome"], option["amount"], option["rate"]) > base, (c["vector"], option)
            if d["outcome"] == "COUNTER_OFFER":             # «как получить всю сумму» — только то, что даёт больше
                assert Decimal(str(option["amount"])) > Decimal(str(offer["amount"])), (c["vector"], option)


def test_factor_target_moves_to_the_better_interval(cases, pol):
    card = pol["scorecard"]
    for c in cases:
        for lever in levers.factor_levers(c["facts"], c["facts"]["segment"], card):
            bins = card["factors"][lever["factor"]]["bins"]
            target = lever["target"] - 1e-6 if lever["way"] == "below" else \
                lever["target"] + 1e-6 if lever["way"] == "above" else lever["target"]
            assert _points(target, bins) == lever["points"] + lever["gain"], (lever, c["vector"])
