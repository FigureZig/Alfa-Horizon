"""K4 — погашение из поступлений: стресс-тест на трёх худших месяцах решает, какой график рекомендовать."""

from decimal import Decimal

from app.domain.repayment import compare


def test_stable_inflows_keep_the_fixed_schedule():
    plan = compare([1_500_000] * 12, 400_000, "17.0", 12)
    assert plan["recommendation"] == "fixed" and plan["fixed"]["comfortable"]
    assert plan["from_inflows"]["months"] == 3                      # 12% от 1,5 млн ≈ 180 тыс. в месяц


def test_weak_months_switch_to_a_share_of_inflows():
    inflows = [3_000_000] * 9 + [200_000] * 3                        # сезонный провал: три слабых месяца
    plan = compare(inflows, 3_000_000, "18.0", 24)
    assert plan["fixed"]["worst3_share"] > 0.5 and plan["recommendation"] == "from_inflows"
    assert plan["from_inflows"]["months"] is not None and plan["from_inflows"]["min_paid"] >= Decimal(20_000)


def test_numbers_hold_together():
    plan = compare([800_000, 1_200_000, 950_000] * 4, 1_000_000, "20.0", 18)
    fixed, flow = plan["fixed"], plan["from_inflows"]
    assert fixed["total_interest"] == fixed["payment"] * 18 - Decimal(1_000_000)
    assert flow["total_interest"] > 0 and flow["max_payment"] >= flow["min_paid"]
