"""Карта на синтетике (docs/12 §7, qa/scoring.py): различает, держит порядок классов, калибруется, PSI ловит сдвиг."""

import pytest

from qa import scoring


@pytest.fixture(scope="module")
def report():
    return scoring.validate(4000)


def test_scorecard_discriminates(report):
    assert report["auc"] >= 0.68 and report["ks"] >= 0.25


def test_default_rate_grows_from_a_to_d_and_calibration_fits(report):
    rates = [c["dr"] for c in report["calibration"] if c["n"] >= 50]
    assert rates == sorted(rates)
    assert all(c["inside"] for c in report["recalibrated"] if c["n"] >= 100)


def test_psi_is_quiet_on_the_same_portfolio_and_loud_under_stress(report):
    assert report["psi_fresh"] < 0.1 < 0.25 < report["psi_stress"]


def test_strong_factors_are_monotone(report):
    strong = {f["factor"]: f for f in report["factors"]}
    assert strong["F4_debt_load"]["monotone"] and strong["F5_delinquency"]["monotone"]
    assert strong["F5_delinquency"]["iv"] > 0.1
