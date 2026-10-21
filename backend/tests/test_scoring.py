import pytest

from app.domain.scoring import score

CLEAN = {"age_months": 24, "inflow_cv": 0.25, "inflow_trend": 0.0, "debt_load": 0.17, "max_overdue_days": 0,
         "bki_requests_30d": 1, "tax_debt": 0}


def test_points_and_class(pol):
    r = score(CLEAN, "IP", pol["scorecard"])
    assert r["score"] == 600 + 0 + 15 + 0 + 10 + 40 + 10 + 20      # F9 у ИП неизвестен → 0
    assert r["class"] == "B"
    assert "F9_bank_share" in r["missing"]


def test_pd_scale(pol):
    card = pol["scorecard"]
    assert score({}, "IP", {**card, "factors": {}})["pd"] == pytest.approx(1 / 16, abs=1e-4)   # 600 баллов → odds 15


@pytest.mark.parametrize("total,cls", [(700, "A"), (699, "B"), (640, "B"), (639, "C"), (560, "C"), (559, "D")])
def test_class_thresholds(pol, total, cls):
    card = {**pol["scorecard"], "factors": {}, "base": total}
    assert score({}, "IP", card)["class"] == cls


def test_unknown_bki_gives_zero_points(pol):
    full = score(CLEAN, "IP", pol["scorecard"])
    info_only = score(CLEAN, "IP", pol["scorecard"], skip_sources=("bki",))             # без согласия
    nothing = score(CLEAN, "IP", pol["scorecard"], skip_sources=("bki", "bki_info"))   # БКИ лежит целиком
    assert full["score"] - info_only["score"] == 10 + 40
    assert full["score"] - nothing["score"] == 10 + 40 + 10
    assert {"F4_debt_load", "F5_delinquency", "F6_credit_hunger"} <= set(nothing["missing"])


def test_monotonic_overdue_never_helps(pol):
    base = score(CLEAN, "IP", pol["scorecard"])["score"]
    for days in (3, 20, 60):
        assert score({**CLEAN, "max_overdue_days": days}, "IP", pol["scorecard"])["score"] < base


def test_profit_only_for_companies(pol):
    factors = {c["factor"] for c in score({**CLEAN, "net_profit": 1}, "IP", pol["scorecard"])["contributions"]}
    assert "F8_profitability" not in factors
