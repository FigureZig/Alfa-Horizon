from decimal import Decimal

import pytest

from app.domain import calc


def float_annuity(p: float, rate: float, n: int) -> float:
    r = rate / 1200
    return p * r * (1 + r) ** n / ((1 + r) ** n - 1)


@pytest.mark.parametrize("principal,rate,months", [(5_000_000, "23.2", 24), (12_000_000, "18.4", 24), (400_000, "17.0", 12)])
def test_annuity_matches_formula(principal, rate, months):
    expected = float_annuity(principal, float(rate), months)
    assert float(calc.annuity_payment(principal, rate, months)) == pytest.approx(expected, abs=0.01)


def test_max_principal_is_inverse_of_payment():
    pay = calc.annuity_payment(3_200_000, "22.7", 24)
    assert abs(calc.max_principal(pay, "22.7", 24) - 3_200_000) < 1


def test_schedule_repays_exactly():
    rows = calc.annuity_schedule(1_000_000, "21.3", 18)
    assert sum(r["principal"] for r in rows) == Decimal("1000000.00")
    assert rows[-1]["balance"] == 0
    assert len(rows) == 18


def test_zero_rate():
    assert calc.annuity_payment(1200, 0, 12) == Decimal("100.00")
    assert calc.max_principal(100, 0, 12) == Decimal("1200.00")


def test_overdraft_interest_by_days():
    assert calc.overdraft_interest(400_000, "17.0", 30) == Decimal("5589.04")


def test_rounding_helpers():
    assert calc.round_to("2.75", "0.5") == Decimal("3.0")
    assert calc.round_to("2.25", "0.5") == Decimal("2.5")
    assert calc.floor_to("3255300", 100_000) == 3_200_000


def test_payoff_from_inflows_share_and_floor():
    assert calc.payoff_from_inflows(400_000, "17.0", [1_500_000] * 6) == 3          # 12% от 1,5 млн ≈ 180 тыс. в месяц
    assert calc.payoff_from_inflows(100_000, "17.0", [0] * 6) == 6                  # минимум 20 тыс. в месяц
    assert calc.payoff_from_inflows(10_000_000, "17.0", [100_000] * 3) is None
