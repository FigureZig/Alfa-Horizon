"""K4 — погашение из поступлений (docs/03): фиксированный график против доли поступлений на истории счёта клиента.

Фиксированный аннуитет сравниваем с поступлениями по месяцам и отдельно — с тремя худшими месяцами (стресс-тест).
Схема «доля поступлений»: каждый месяц списывается доля пришедших денег, но не меньше минимума, — прогон по истории
клиента по кругу. Чистая функция: каждое число видно в ответе.
"""

from decimal import Decimal

from .calc import annuity_payment, dec, money, monthly_rate


def compare(inflows: list, amount, annual_pct, term_months: int, *, share="0.12", min_payment="20000",
            stress_max="0.5") -> dict:
    hist = [dec(x) for x in inflows][-12:] or [Decimal(0)]
    principal = money(dec(amount))
    fixed = annuity_payment(principal, annual_pct, term_months)
    worst = sorted(hist)[:3]
    worst_avg = money(sum(worst) / len(worst))
    worst_share = round(float(fixed / worst_avg), 3) if worst_avg > 0 else None
    debt, rate, part, floor = principal, monthly_rate(annual_pct), dec(share), dec(min_payment)
    interest, payments = Decimal(0), []
    while debt > 0 and len(payments) < term_months * 3:
        accrued = money(debt * rate)
        debt, interest = debt + accrued, interest + accrued
        paid = min(debt, max(money(hist[len(payments) % len(hist)] * part), floor))
        debt -= paid
        payments.append(paid)
    comfortable = worst_share is not None and worst_share <= float(stress_max)
    return {
        "fixed": {"payment": fixed, "term_months": term_months, "total_interest": money(fixed * term_months - principal),
                  "worst3_inflow_avg": worst_avg, "worst3_share": worst_share, "comfortable": comfortable},
        "from_inflows": {"share": float(part), "min_payment": floor, "months": len(payments) if debt <= 0 else None,
                         "total_interest": money(interest), "max_payment": max(payments, default=Decimal(0)),
                         "min_paid": min(payments, default=Decimal(0))},
        "recommendation": "fixed" if comfortable else "from_inflows",
        "stress_max": float(stress_max),
    }
