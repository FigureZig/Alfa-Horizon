"""K1 — прогноз остатка: история кейса S7 и арифметика, которую видно на графике."""

from datetime import timedelta
from decimal import Decimal

from app.domain import forecast
from app.features import INFLOW_SKIP, account_operations

from .conftest import TODAY, mock_payloads


def run(inn: str, ops_patch=None) -> dict:
    tx = mock_payloads(inn)["bank_tx"]
    ops = account_operations(tx)
    if ops_patch:
        ops = ops_patch(ops)
    return forecast.forecast(ops, Decimal(tx["balance"]["amount"]), TODAY, skip=INFLOW_SKIP)


def test_s7_coffee_shop_runs_short_on_the_28th():
    """Кейс: ИП, 28-го не хватит на налоги и зарплату — из регулярных платежей выписки, а не из сценария."""
    fc = run("770100000079")
    assert fc["status"] == "CASH_GAP" and str(fc["cash_gap"]["date"]) == "2026-10-28"
    assert {op["title"] for op in fc["operations"]} == {"Аренда помещения", "Зарплата сотрудникам, вторая половина",
                                                        "Поставщики кофе и продуктов", "НДФЛ и страховые взносы"}
    assert fc["cash_gap"]["amount"] < 400_000                              # предодобренный овердрафт S7 закрывает разрыв


def test_points_are_inflow_minus_scheduled_payments():
    fc = run("770100000079")
    paid = {}
    for op in fc["upcoming"]:
        paid[op["date"]] = paid.get(op["date"], Decimal(0)) + op["amount"]
    for prev, point in zip(fc["points"], fc["points"][1:], strict=False):
        assert point["date"] - prev["date"] == timedelta(days=1)
        assert point["balance"] - prev["balance"] == fc["daily_inflow"] + paid.get(point["date"], Decimal(0))


def test_regular_payment_needs_three_repeats_and_never_improves_the_forecast():
    base = run("7701000019")
    one_off = run("7701000019", lambda ops: [*ops, {**ops[-1], "amount": Decimal("-5000000"), "purpose": "Разовая покупка",
                                                    "category": "other"}])
    assert [r["purpose"] for r in one_off["regular_outflows"]] == [r["purpose"] for r in base["regular_outflows"]]
    doubled = run("7701000019", lambda ops: [{**op, "amount": op["amount"] * 2} if op["amount"] < 0 else op for op in ops])
    assert min(p["balance"] for p in doubled["points"]) <= min(p["balance"] for p in base["points"])
