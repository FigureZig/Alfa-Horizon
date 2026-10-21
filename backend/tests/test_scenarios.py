"""Golden по демо-миру: каждый сценарий из seed/personas.yaml проходит путь «моки → факты → движок»."""

from decimal import Decimal

import pytest

from app.domain import engine

from .conftest import WORLD, facts_of

SCENARIOS = [c for c in WORLD["companies"] if c.get("scenario")]


def check(decision: dict, expect: dict) -> None:
    assert decision["outcome"] == expect["outcome"], decision["reasons"]
    codes = {r["code"] for r in decision["reasons"]}
    for key, value in expect.items():
        offer = decision["offer"] or {}
        match key:
            case "outcome":
                pass
            case "kind":
                assert decision["kind"] == value
            case "counter":
                assert decision["counter"] == value
            case "asks":
                assert decision["asks"] == value
            case "reasons_include":
                assert set(value) <= codes, codes
            case "risk_class":
                assert decision["risk"]["class"] == value
            case "score":
                assert decision["risk"]["score"] == value
            case "rate":
                assert offer["rate"]["total"] == Decimal(value)
            case "amount":
                assert offer["amount"] == Decimal(value)
            case "product":
                assert offer["product"] == value
            case "alternative":
                alt = decision["alternatives"][0]
                assert (alt["amount"], alt["termMonths"]) == (Decimal(value["amount"]), value["term_months"])
            case _:
                raise AssertionError(f"неизвестное поле expect: {key}")


@pytest.mark.parametrize("company", SCENARIOS, ids=[c["key"] for c in SCENARIOS])
def test_scenario(pol, company):
    sc = company["scenario"]
    check(engine.decide(facts_of(company["inn"]), sc["request"], pol, "commit"), sc["expect"])
    if "expect_without_bki" in sc:
        check(engine.decide(facts_of(company["inn"], without=("bki",)), sc["request"], pol, "commit"),
              sc["expect_without_bki"])


def test_every_non_approve_has_a_reason(pol):
    for company in SCENARIOS:
        d = engine.decide(facts_of(company["inn"]), company["scenario"]["request"], pol, "commit")
        if d["outcome"] != "APPROVE":
            assert d["reasons"], company["key"]


def test_simulate_equals_commit_when_data_complete(pol):
    for company in SCENARIOS:
        facts, req = facts_of(company["inn"]), company["scenario"]["request"]
        assert engine.decide(facts, req, pol, "simulate")["outcome"] == engine.decide(facts, req, pol, "commit")["outcome"]


def test_provisional_offer_when_bki_down_and_small_amount(pol):
    smirnova = next(c for c in SCENARIOS if c["key"] == "smirnova")
    d = engine.decide(facts_of(smirnova["inn"], without=("bki",)), smirnova["scenario"]["request"], pol, "commit")
    assert "PROVISIONAL" in d["flags"]
    assert d["status"] == "OFFERED"
    assert d["offer"]["rate"]["total"] == Decimal("17.0")         # информационная часть КИ держит класс B — условия те же


def test_preapproval_without_consent_uses_bki_info_part(pol):
    facts = facts_of("770100000079", without=("bki",))             # до согласия полного отчёта нет
    items = {i["product"]: i for i in engine.preapprove(facts, pol, "cash_gap", 400_000, 12)}
    overdraft = items["OVERDRAFT"]["decision"]
    assert items["OVERDRAFT"]["label"] == "PREAPPROVED"
    assert overdraft["risk"]["score"] == 645 and overdraft["risk"]["class"] == "B"
    assert overdraft["offer"]["amount"] == Decimal("400000.00")


def test_picker_shows_products_by_industry(pol):
    cloud = facts_of("7701000080")                                  # ИТ: инвестиционного кредита нет
    items = {i["product"]: i["label"] for i in engine.preapprove(cloud, pol, "equipment", 5_000_000, 36)}
    assert items == {"INVESTMENT": "UNAVAILABLE", "EXPRESS": "PREAPPROVED"}
    farm = facts_of("7701000072")                                   # аграрии: сезонный кредит есть
    labels = {i["product"]: i["label"] for i in engine.preapprove(farm, pol, "stock", 8_000_000, 10)}
    assert labels["AGRO_SEASONAL"] == "PREAPPROVED"

