"""Кредитные калькуляторы. Деньги — Decimal (не float), ставки — % годовых."""

from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def dec(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def money(x) -> Decimal:
    return dec(x).quantize(CENT, ROUND_HALF_UP)


def round_to(x, step) -> Decimal:
    """Арифметическое округление до шага: 2,75 → 3,0 при шаге 0,5."""
    step = dec(step)
    return (dec(x) / step).quantize(Decimal(1), ROUND_HALF_UP) * step


def floor_to(x, step) -> Decimal:
    step = dec(step)
    return (dec(x) / step).to_integral_value(ROUND_FLOOR) * step


def monthly_rate(annual_pct) -> Decimal:
    return dec(annual_pct) / Decimal(1200)


def annuity_payment(principal, annual_pct, months: int) -> Decimal:
    """Аннуитетный платёж: P·r·(1+r)^n / ((1+r)^n − 1)."""
    if months <= 0:
        raise ValueError("months must be positive")
    p, r = dec(principal), monthly_rate(annual_pct)
    if r == 0:
        return money(p / months)
    k = (1 + r) ** months
    return money(p * r * k / (k - 1))


def max_principal(payment, annual_pct, months: int) -> Decimal:
    """Обратная задача: какую сумму покрывает ежемесячный платёж за n месяцев."""
    a, r = dec(payment), monthly_rate(annual_pct)
    if a <= 0 or months <= 0:
        return Decimal(0)
    if r == 0:
        return money(a * months)
    k = (1 + r) ** months
    return money(a * (k - 1) / (r * k))


def interest_payment(principal, annual_pct) -> Decimal:
    """Проценты за месяц: при погашении долга в конце срока и по овердрафту при полной выборке лимита."""
    return money(dec(principal) * monthly_rate(annual_pct))


def payment(repayment: str, principal, annual_pct, months: int) -> Decimal:
    if repayment == "annuity":
        return annuity_payment(principal, annual_pct, months)
    return interest_payment(principal, annual_pct)


def annuity_schedule(principal, annual_pct, months: int) -> list[dict]:
    """График платежей; последний платёж закрывает остаток до копейки."""
    pay, r = annuity_payment(principal, annual_pct, months), monthly_rate(annual_pct)
    balance, rows = money(principal), []
    for n in range(1, months + 1):
        interest = money(balance * r)
        body = balance if n == months else pay - interest
        balance = money(balance - body)
        rows.append({"n": n, "payment": body + interest, "interest": interest, "principal": body, "balance": balance})
    return rows


def overdraft_interest(balance, annual_pct, days: int, basis: int = 365) -> Decimal:
    """Проценты за дни пользования овердрафтом: остаток × ставка × дни / 365."""
    return money(dec(balance) * dec(annual_pct) / 100 * days / basis)


def payoff_from_inflows(debt, annual_pct, inflows, share="0.12", min_payment="20000") -> int | None:
    """K4: за сколько месяцев уйдёт долг, если списывать долю каждого поступления, но не меньше минимума."""
    debt, r, share, floor = money(debt), monthly_rate(annual_pct), dec(share), dec(min_payment)
    for month, inflow in enumerate(inflows, start=1):
        debt = money(debt * (1 + r))
        debt -= min(debt, max(money(dec(inflow) * share), floor))
        if debt <= 0:
            return month
    return None
