"""K1 — радар кассового разрыва (docs/03): прогноз остатка по дням на горизонт из истории счёта.

Регулярные списания находим по повторяемости: одно назначение в один день месяца — не меньше чем в 3 из 4 последних
полных месяцев, сумма — медиана. Поступления — среднедневная выручка за 3 последних полных месяца (без кредитов,
своих переводов и депозита). Остаток сегодня — из выписки. Разрыв — самая глубокая точка ниже нуля, его операции —
регулярные списания до неё. Чистая функция: каждое число видно на графике и в «почему так».
"""

import calendar
from datetime import date, timedelta
from decimal import Decimal
from statistics import median

HORIZON_DAYS = 30
LOOKBACK_MONTHS = 4                 # где ищем повторы
MIN_REPEATS = 3                     # сколько раз из LOOKBACK_MONTHS платёж должен повториться
INFLOW_MONTHS = 3                   # по скольким месяцам средние поступления
NOT_REGULAR = {"deposit"}           # размещение свободного остатка — не обязательный платёж


def _month(d: date, back: int) -> str:
    y, m = divmod(d.year * 12 + d.month - 1 - back, 12)
    return f"{y:04d}-{m + 1:02d}"


def regular_outflows(operations: list[dict], today: date) -> list[dict]:
    """Списания, которые повторяются в одни и те же дни месяца: зарплата, аренда, налоги, кредиты, поставщики."""
    months = {_month(today, back) for back in range(1, LOOKBACK_MONTHS + 1)}
    seen: dict[tuple[str, int], dict[str, Decimal]] = {}
    for op in operations:
        if op["amount"] >= 0 or op["category"] in NOT_REGULAR or op["date"].strftime("%Y-%m") not in months:
            continue
        seen.setdefault((op["purpose"], op["date"].day), {})[op["date"].strftime("%Y-%m")] = -op["amount"]
    return sorted(({"purpose": purpose, "day": day, "amount": Decimal(median(amounts.values())).quantize(Decimal("0.01")),
                    "repeats": len(amounts)}
                   for (purpose, day), amounts in seen.items() if len(amounts) >= MIN_REPEATS),
                  key=lambda r: (r["day"], r["purpose"]))


def daily_inflow(operations: list[dict], today: date, skip: set[str]) -> Decimal:
    months = [_month(today, back) for back in range(1, INFLOW_MONTHS + 1)]
    total = sum((op["amount"] for op in operations
                 if op["amount"] > 0 and op["category"] not in skip and op["date"].strftime("%Y-%m") in months), Decimal(0))
    days = sum(calendar.monthrange(int(m[:4]), int(m[5:]))[1] for m in months)
    return (total / days).quantize(Decimal("0.01"))


def forecast(operations: list[dict], balance: Decimal, today: date, *, skip: set[str], horizon: int = HORIZON_DAYS,
             extra_regular: tuple | list = (), credit_line: Decimal | None = None) -> dict:
    """operations — операции счёта: {date, amount (со знаком), purpose, category}; balance — остаток на сегодня.
    extra_regular — платежи, которых в истории ещё нет (кредит, только что выданный банком): {purpose, day, amount};
    credit_line — подключённый овердрафт: минус в его пределах — не разрыв, а «покроет лимит» (COVERED)."""
    regular = sorted([*regular_outflows(operations, today), *extra_regular], key=lambda r: (r["day"], r["purpose"]))
    inflow = daily_inflow(operations, today, skip)
    points, scheduled, running = [{"date": today, "balance": balance}], [], balance
    for step in range(1, horizon + 1):
        day = today + timedelta(days=step)
        last = calendar.monthrange(day.year, day.month)[1]
        due = [r for r in regular if min(r["day"], last) == day.day]
        running += inflow - sum((r["amount"] for r in due), Decimal(0))
        scheduled += [{"date": day, "title": r["purpose"], "amount": -r["amount"]} for r in due]
        points.append({"date": day, "balance": running})
    deepest = min(points, key=lambda p: p["balance"])
    gap = deepest["balance"] < 0
    first_negative = next((p["date"] for p in points if p["balance"] < 0), None)
    cash_gap = {"date": deepest["date"], "amount": -deepest["balance"], "first_negative_date": first_negative}
    covered = gap and credit_line is not None and -deepest["balance"] <= credit_line
    return {
        "status": "COVERED" if covered else "CASH_GAP" if gap else "HEALTHY", "horizon_days": horizon, "balance": balance,
        "daily_inflow": inflow, "points": points, "regular_outflows": regular, "cash_gap": cash_gap if gap else None,
        "credit_line": credit_line,
        "operations": [op for op in scheduled if op["date"] <= deepest["date"]] if gap else [],
        "upcoming": scheduled,
    }


def cover_cost(points: list[dict], annual_pct) -> dict | None:
    """Сколько стоит закрыть разрыв овердрафтом: проценты только за дни в минусе и только на сумму минуса."""
    negative = [-p["balance"] for p in points if p["balance"] < 0]
    if not negative:
        return None
    interest = sum(negative, Decimal(0)) * Decimal(str(annual_pct)) / 100 / 365
    return {"amount": max(negative), "days": len(negative), "interest": interest.quantize(Decimal("1"))}
