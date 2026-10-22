"""Флаги конструктора своей компании (seed/persona_flags.yaml) реально меняют решение: на эталонной заявке флаг даёт
обещанную причину, продукт или отказ источника — а без флага этого нет. Флаг-пустышку тест не пропустит."""

import pytest

from app.domain import catalog, engine
from app.features import company_facts
from seed import flags, world

from .conftest import TODAY

REQUEST = {"product": "EXPRESS", "amount": 1_500_000, "term_months": 24, "goal": "growth"}


def _decide(spec: dict, number: int, pol: dict) -> tuple[dict, dict]:
    company, people = world.custom(spec, number, TODAY)
    assert not world.validate(company, people, TODAY)
    facts = company_facts(company["inn"], world.served(company, people, TODAY), TODAY)
    return facts, engine.decide(facts, REQUEST, pol, "commit")


def _seen(decision: dict) -> set[str]:
    return {r["code"] for r in decision["reasons"]} | set((decision.get("risk") or {}).get("weak", []))


CASES = [(name, form) for name, flag in flags.catalog()["flags"].items() for form in flag["forms"]]


@pytest.mark.parametrize(("name", "form"), CASES, ids=[f"{n}-{f}" for n, f in CASES])
def test_flag_changes_the_decision(name, form, pol):
    expect = flags.catalog()["flags"][name]["expect"]
    base = {"kind": form, "participants": 1}
    spec, faults = flags.apply(base, [name])
    if "fault" in expect:
        assert [f["source"] for f in faults] == [expect["fault"]]
        return
    facts0, plain = _decide(base, 600, pol)
    facts1, flagged = _decide(spec, 600, pol)
    if "reason" in expect:
        assert expect["reason"] in _seen(flagged) and expect["reason"] not in _seen(plain), (name, form)
    if "product" in expect:
        sections = (facts0.get("section"), facts0.get("segment"))
        assert expect["product"] in catalog.available_products(pol, *sections)
        req = {**REQUEST, "product": expect["product"], "goal": "contract"}
        assert engine.decide(facts1, req, pol, "commit")["outcome"] != engine.decide(facts0, req, pol, "commit")["outcome"]


def test_catalog_is_complete_and_readable():
    cat = flags.catalog()
    for name, flag in cat["flags"].items():
        assert flag["group"] in cat["groups"], name
        assert flag["title"]["ru"] and flag["title"]["en"] and flag["effect"]["ru"] and flag["effect"]["en"], name
        assert set(flag["forms"]) <= {"IP", "LLC", "JSC"} and flag["expect"], name
