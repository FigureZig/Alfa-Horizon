"""Отрасли, ставка и цена риска — то, из чего складываются деньги (docs/13)."""

from decimal import Decimal

import pytest

from app.domain import catalog
from app.domain.okved import section_of


@pytest.mark.parametrize("code,section", [("56.30", "I"), ("01.11", "A"), ("10.71", "C"), ("46.90", "G"),
                                          ("49.41", "H"), ("62.01", "J"), ("81.21", "N"), ("92.10", "R"), ("x", None)])
def test_okved_section(code, section):
    assert section_of(code) == section


@pytest.mark.parametrize("section,bucket,spread", [
    ("I", "short", "0.0"),    # 17,01 − 17,85 < 0 → пол
    ("I", "long", "2.6"),
    ("G", "long", "5.7"),
    ("C", "long", "2.4"),
    ("H", "long", "5.3"),
    ("J", "long", "7.3"),
    ("A", "short", "0.0"),
    ("M", "long", "0.0"),
    ("Q", "short", "2.8"),    # раздела нет в табл. 11 → строка «Прочее»
    ("Q", "long", "4.4"),
])
def test_industry_spread(pol, section, bucket, spread):
    assert catalog.industry_spread(pol["market"], section, bucket) == Decimal(spread)


@pytest.mark.parametrize("risk_class,security,spread", [
    ("A", "none", "2.0"), ("B", "none", "3.0"), ("C", "none", "5.0"), ("D", "none", "11.5"),
    ("B", "owner_guarantee", "3.0"), ("B", "guarantor", "2.5"), ("C", "guarantor", "4.0"), ("C", "collateral", "3.5"),
])
def test_risk_spread_from_expected_loss(pol, risk_class, security, spread):
    assert catalog.risk_spread(pol["risk_pricing"], risk_class, security) == Decimal(spread)


def test_rate_is_sum_of_parts(pol):
    r = catalog.rate(pol, "I", 12, "B", "none")
    assert r["total"] == r["key_rate"] + r["industry"] + r["risk"] == Decimal("17.0")


def test_products_depend_on_industry(pol):
    assert "INVESTMENT" not in catalog.available_products(pol, "J", "LLC")      # ИТ: нет залоговой базы
    assert "AGRO_SEASONAL" in catalog.available_products(pol, "A", "LLC")
    assert "AGRO_SEASONAL" not in catalog.available_products(pol, "G", "LLC")
    assert catalog.available_products(pol, "I", "IP") == ["OVERDRAFT", "EXPRESS", "INVESTMENT"]


@pytest.mark.parametrize("okved,section,ok", [("64.19", "K", False), ("92.10", "R", False), ("93.11", "R", True),
                                              ("84.11", "O", False), ("47.11", "G", True)])
def test_industry_stop_list(pol, okved, section, ok):
    assert catalog.section_check(pol, okved, section)[0] is ok


def test_every_product_in_sections_and_goals_exists(pol):
    referenced = {p for s in pol["sections"].values() for p in s["products"]} | \
                 {p for g in pol["goals"].values() for p in g["products"]}
    assert referenced <= set(pol["products"])
