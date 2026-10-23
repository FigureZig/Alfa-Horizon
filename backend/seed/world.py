"""Мир симулятора: из описания компании — ответы всех внешних источников в форматах docs/09.

Чистые функции без записи на диск. Генератор моков пишет их в wiremock/, симулятор ставит в WireMock на лету
(«своя персона»), тесты строят мир в памяти. validate() — правила корректности: контрольные цифры, даты,
согласованность источников между собой. Платежи по кредитам, категория МСП и платежи в выписке банка
не задаются руками, а выводятся, поэтому разойтись не могут.
"""

import calendar
import json
import random
import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import yaml

from app.domain.calc import annuity_payment, monthly_rate
from app.domain.okved import section_of

WORLD = Path(__file__).resolve().parent / "personas.yaml"

# Источник (policy/sources.yaml) → папка с телами ответов в wiremock/__files
FILES = {
    "egrul": "egrul", "egrip": "egrip", "rsmp": "fns/rsmp", "sshr": "fns/sshr", "paytax": "fns/paytax",
    "debtam": "fns/debtam", "snr": "fns/snr", "girbo": "girbo/bfo", "legal": "legal", "bank_access": "bank/access",
    "bank_charter": "bank/charter", "bank_tx": "bank/tx", "eis": "eis", "bki": "bki", "bki_info": "bki-info", "mchd": "mchd",
}
POWERS = {"CREDIT_AGREEMENT_SIGN": "Подписание кредитного договора"}   # в проде — коды классификатора ЕСНСИ (docs/09)
OPF = {"LLC": ("12300", "Общество с ограниченной ответственностью"),
       "JSC": ("12267", "Непубличное акционерное общество")}
# 209-ФЗ ст. 4: численность ≤ 15 / 100 / 250 чел., доход ≤ 120 млн / 800 млн / 2 млрд ₽ (ПП РФ № 265; docs/10 L9, L10).
# Категория — по большему из двух показателей.
MSP_LIMITS = ((1, 15, 120_000_000), (2, 100, 800_000_000), (3, 250, 2_000_000_000))
FLAGS = {"liquidation", "bankruptcy", "unreliable_eio", "disqualified_eio"}
UL_ONLY_FLAGS = {"liquidation", "unreliable_eio", "disqualified_eio"}     # отметки ЕГРЮЛ; в ЕГРИП их нет
BIK = "044525777"                    # БИК банка в моках — синтетический
_W10 = (2, 4, 10, 3, 5, 9, 4, 6, 8)
_W11 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
_W12 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)


def load() -> dict:
    return yaml.safe_load(WORLD.read_text("utf-8"))


# ── идентификаторы: алгоритмы контрольных цифр ФНС и ПФР ────────────────────────────────────────────────────────


def _check(digits: str, weights: tuple[int, ...]) -> int:
    return sum(int(d) * w for d, w in zip(digits, weights, strict=False)) % 11 % 10


def inn_ul(base9: str) -> str:
    return base9 + str(_check(base9, _W10))


def inn_fl(base10: str) -> str:
    n11 = _check(base10, _W11)
    return base10 + str(n11) + str(_check(base10 + str(n11), _W12))


def inn_valid(inn: str) -> bool:
    if not inn.isdigit():
        return False
    if len(inn) == 10:
        return inn == inn_ul(inn[:9])
    return len(inn) == 12 and inn == inn_fl(inn[:10])


def ogrn(year: int, region: str, number: int, ip: bool = False) -> str:
    """ОГРН: 1 + год + регион + номер записи (7 знаков) + контрольная; ОГРНИП: 3 + год + регион + 9 знаков + контрольная."""
    base = f"3{year % 100:02d}{region}{number:09d}" if ip else f"1{year % 100:02d}{region}{number:07d}"
    return base + str(int(base) % (13 if ip else 11) % 10)


def ogrn_valid(value: str) -> bool:
    if not value.isdigit() or len(value) not in (13, 15):
        return False
    return int(value[-1]) == int(value[:-1]) % (13 if len(value) == 15 else 11) % 10


def snils(base9: str) -> str:
    total = sum(int(d) * w for d, w in zip(base9, range(9, 0, -1), strict=True))
    check = total if total < 100 else (0 if total in (100, 101) else total % 101 % 100)
    return f"{base9}{check:02d}"


def account(inn: str, bik: str = BIK) -> str:
    """Расчётный счёт: 40702 — юрлицо, 40802 — ИП; 810 — рубли; 9-я цифра — ключ по БИК (алгоритм ЦБ, веса 7-1-3)."""
    base = ("40702" if len(inn) == 10 else "40802") + "810" + "0" + inn[-11:].rjust(11, "0")
    digits = bik[-3:] + base
    key = sum(int(d) * w for d, w in zip(digits, (7, 1, 3) * 8, strict=False)) % 10 * 3 % 10
    return base[:8] + str(key) + base[9:]


def account_valid(number: str, bik: str = BIK) -> bool:
    if len(number) != 20 or not number.isdigit():
        return False
    return sum(int(d) * w for d, w in zip(bik[-3:] + number, (7, 1, 3) * 8, strict=False)) % 10 == 0


def msp_category(headcount: int, revenue: float) -> int | None:
    by_head = next((cat for cat, people, _ in MSP_LIMITS if headcount <= people), None)
    by_revenue = next((cat for cat, _, limit in MSP_LIMITS if revenue <= limit), None)
    return None if by_head is None or by_revenue is None else max(by_head, by_revenue)


def is_ul(c: dict) -> bool:
    return len(c["inn"]) == 10


def revenue_rub(c: dict) -> float:
    return c["girbo"]["revenue"] * 1000 if c.get("girbo") else float(sum(c["inflows"]))


def credits(c: dict) -> list[dict]:
    """Кредиты из описания [сумма, ставка, срок, оплачено месяцев, просрочка дней] → платёж и остаток по аннуитету."""
    out = []
    for amount, rate, term, paid, overdue in c["bki"]["credits"]:
        pay = annuity_payment(amount, rate, term)
        r, grown = monthly_rate(rate), (1 + monthly_rate(rate)) ** paid
        debt = (Decimal(amount) * grown - pay * (grown - 1) / r).quantize(Decimal("0.01"), ROUND_HALF_UP)
        out.append({"amount": amount, "rate": rate, "term": term, "paid": paid, "overdue": overdue,
                    "payment": pay, "debt": max(debt, Decimal(0))})
    return out


# ── проверка описания ─────────────────────────────────────────────────────────────────────────────────────────────


def validate(c: dict, people: dict, today: date) -> list[str]:
    """Пустой список — описание корректно. Иначе — что именно не так (генерация не пойдёт)."""
    errors, ul = [], is_ul(c)
    say = errors.append
    if not inn_valid(c["inn"]):
        say("ИНН с неверной контрольной цифрой")
    for poa in c.get("poa", []):
        if not ul:
            say("МЧД в мире — только у юрлиц (доверенность ИП не моделируем)")
        if poa["person"] not in people:
            say(f"представитель по МЧД {poa['person']} не описан в people")
        if set(poa["powers"]) - set(POWERS):
            say(f"неизвестные полномочия МЧД: {sorted(set(poa['powers']) - set(POWERS))}")
    if not ogrn_valid(c["ogrn"]) or len(c["ogrn"]) != (13 if ul else 15):
        say("ОГРН/ОГРНИП неверный или не того типа")
    else:
        if c["ogrn"][1:3] != c["registered"][2:4]:
            say("год в ОГРН не совпадает с датой регистрации")
        if c["ogrn"][3:5] != c["inn"][:2]:
            say("регион в ОГРН и ИНН разный")
    if c["registered"] > today.isoformat():
        say("дата регистрации в будущем")
    if section_of(c["okved"][0]) is None:
        say(f"ОКВЭД {c['okved'][0]} не из классификатора")
    if len(c["inflows"]) != 12 or min(c["inflows"]) <= 0:
        say("поступления — ровно 12 положительных месяцев")
    if c["headcount"] <= 0:
        say("численность должна быть положительной")
    if msp_category(c["headcount"], revenue_rub(c)) is None:
        say("компания не субъект МСП по численности или доходу")
    unknown = set(c.get("flags", [])) - FLAGS
    if unknown:
        say(f"неизвестные флаги: {sorted(unknown)}")
    for amount, rate, term, paid, overdue in c["bki"]["credits"]:
        if amount <= 0 or rate <= 0 or not 0 <= paid < term or overdue < 0:
            say("кредит в БКИ: сумма и ставка > 0, оплачено меньше срока")
    refs = [p for p, _ in c.get("eio", [])] + [p for p, _ in c.get("participants", [])] + [p for p, _ in c["access"]]
    refs += [c[k] for k in ("owner", "kyc_director") if c.get(k)]
    for key in refs:
        if key not in people:
            say(f"человек {key} не описан")
        elif not inn_valid(people[key]["inn"]) or len(people[key]["inn"]) != 12:
            say(f"ИНН человека {key} неверный")
    if ul:
        if not c.get("eio"):
            say("у юрлица нет руководителя")
        if c.get("opf", "LLC") == "LLC" and sum(share for _, share in c.get("participants", [])) != 100:
            say("доли участников ООО в сумме не 100%")
        if not c.get("girbo") or c["girbo"]["assets"] <= 0:
            say("у юрлица нет отчётности в ГИР БО")
    else:
        if c.get("participants") or c.get("eio") or c.get("girbo") or not c.get("owner"):
            say("у ИП есть только он сам: без участников, директоров и бухотчётности")
        if set(c.get("flags", [])) & UL_ONLY_FLAGS:
            say(f"у ИП не бывает отметок ЕГРЮЛ: {sorted(set(c['flags']) & UL_ONLY_FLAGS)}")
    for k in c.get("eis", []):
        if k["price"] <= 0 or not 0 <= k["advancePercent"] < 100 or k["signDate"] >= k["endDate"]:
            say(f"контракт {k['regNum']}: цена, аванс или даты неверны")
    if c.get("balance") is not None and len(c["inflows"]) == 12 and not errors:
        current = _month_flows(c, today, random.Random(int(c["inn"])))[-1][3]
        start = Decimal(c["balance"]) - sum((_signed(t) for t in current), Decimal(0))
        if start + _dip(current) < 0:                       # счёт без овердрафта: в этом месяце ушёл бы в минус
            say(f"остаток {c['balance']} не сходится с платежами текущего месяца — счёт уходил бы в минус")
    return errors


# ── ответы источников ─────────────────────────────────────────────────────────────────────────────────────────────


def _fio(person: dict) -> dict:
    last, first, middle = person["fio"]
    return {"@Фамилия": last, "@Имя": first, "@Отчество": middle}


def _okved(c: dict) -> dict:
    return {"СвОКВЭДОсн": {"@КодОКВЭД": c["okved"][0], "@НаимОКВЭД": c["okved"][1], "@ПрВерсОКВЭД": "2014"}}


def _months_ago(today: date, months: int, day: int) -> str:
    y, m = divmod(today.year * 12 + today.month - 1 - months, 12)
    return f"{y}-{m + 1:02d}-{min(day, calendar.monthrange(y, m + 1)[1]):02d}"


def egrul(c: dict, people: dict, today: date) -> dict:
    """JSON-зеркало выписки ЕГРЮЛ, формат ФНС 4.06 (docs/09 §2)."""
    flags, (code, opf_name) = set(c.get("flags", [])), OPF[c.get("opf", "LLC")]
    directors = []
    for i, (p, title) in enumerate(c["eio"]):
        record = {"СвФЛ": {**_fio(people[p]), "@ИННФЛ": people[p]["inn"]}, "СвДолжн": {"@ВидДолжн": "02", "@НаимДолжн": title}}
        if i == 0 and "unreliable_eio" in flags:
            record["СвНедДанДолжнФЛ"] = {"@ПризнНедДанДолжнФЛ": "1",
                                         "@ТекстНедДанДолжнФЛ": "сведения недостоверны (проверка регистрирующим органом)"}
        if i == 0 and "disqualified_eio" in flags:
            record["СвДискв"] = {"@ДатаНачДискв": _months_ago(today, 2, 1), "@ДатаОкончДискв": _months_ago(today, -22, 1),
                                "@ДатаРеш": _months_ago(today, 2, 1)}
        directors.append(record)
    ul = {"@ОГРН": c["ogrn"], "@ДатаОГРН": c["registered"], "@ИНН": c["inn"], "@КПП": c["inn"][:4] + "01001",
          "@КодОПФ": code, "@ПолнНаимОПФ": opf_name,
          "СвНаимЮЛ": {"@НаимЮЛПолн": c["name"].replace("ООО ", "ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "),
                       "@НаимЮЛСокр": c["name"]},
          "СвОКВЭД": _okved(c), "СведДолжнФЛ": directors,
          # несколько руководителей по уставу действуют совместно («1») или независимо («2») — ГК ст. 53 п. 1
          "СвПолном": {"@ВидПолном": "1" if c.get("eio_mode") == "joint" else "2"},
          "СвУчредит": {"УчрФЛ": [{"СвФЛ": {**_fio(people[p]), "@ИННФЛ": people[p]["inn"]},
                                   "ДоляУстКап": {"@НоминСтоим": str(share * 100), "РазмерДоли": {"Процент": str(share)}}}
                                  for p, share in c.get("participants", [])]}}
    if "liquidation" in flags:
        ul["СвСтатус"] = {"@КодСтатусЮЛ": "101", "@НаимСтатусЮЛ": "Находится в стадии ликвидации"}
    return {"СвЮЛ": ul}


def egrip(c: dict, people: dict) -> dict:
    return {"СвИП": {"@ОГРНИП": c["ogrn"], "@ДатаОГРНИП": c["registered"], "@ИННФЛ": c["inn"], "@КодВидИП": "1",
                     "СвФЛ": {"ФИОРус": _fio(people[c["owner"]])}, "СвОКВЭД": _okved(c)}}


def fns(c: dict, people: dict) -> dict:
    """Записи открытых наборов ФНС по компании: МСП, численность, налоги, недоимка, спецрежим (XSD в docs/09)."""
    ul, tax = is_ul(c), c.get("tax", {})
    debt, regime, yearly = tax.get("debt", 0), tax.get("regime", "OSN"), sum(c["inflows"])
    who = {"ОргВклМСП": {"@НаимОрг": c["name"], "@ИННЮЛ": c["inn"]}} if ul else \
        {"ИПВклМСП": {"@ИННФЛ": c["inn"], "ФИОИП": _fio(people[c["owner"]])}}
    debts = [] if not debt else [
        {"@НаимНалог": "Налог, взимаемый в связи с применением упрощённой системы налогообложения",
         "@СумНедНалог": f"{debt * 0.7:.2f}", "@СумПени": "0.00", "@СумШтраф": "0.00", "@ОбщСумНедоим": f"{debt * 0.7:.2f}"},
        {"@НаимНалог": "Страховые взносы на обязательное социальное страхование",
         "@СумНедНалог": f"{debt * 0.3:.2f}", "@СумПени": "0.00", "@СумШтраф": "0.00", "@ОбщСумНедоим": f"{debt * 0.3:.2f}"},
    ]
    out = {
        "sshr": {"Документ": {"@ДатаСост": "2025-12-31", "СведССЧР": {"@КолРаб": str(c["headcount"])}}},
        "paytax": {"Документ": {"@ДатаСост": "2025-12-31", "СвУплСумНал": [
            {"@НаимНалог": "Страховые взносы на обязательное пенсионное страхование", "@СумУплНал": f"{yearly * 0.03:.2f}"},
            {"@НаимНалог": "Налог на доходы физических лиц", "@СумУплНал": f"{yearly * 0.015:.2f}"}]}},
        "debtam": {"Документ": {"@ДатаСост": "2026-10-01", "СведНедоим": debts}},
        "snr": {"Документ": {"@ДатаСост": "2025-12-31", "СведСНР": {
            "@ПризнЕСХН": str(int(regime == "ESHN")), "@ПризнУСН": str(int(regime == "USN")),
            "@ПризнАУСН": str(int(regime == "AUSN")), "@ПризнСРП": "0"}}},
    }
    category = msp_category(c["headcount"], revenue_rub(c))
    if category is not None:
        out["rsmp"] = {"Документ": {"@ДатаСост": "2026-10-10", "@ВидСубМСП": "1" if ul else "2", "@КатСубМСП": str(category),
                                    "@ДатаВклМСП": c["registered"], **who, "СвОКВЭД": _okved(c)}}
    return out


def girbo(c: dict) -> list:
    """ГИР БО (bo.nalog.gov.ru): тыс. ₽, строки 1600 = 1300 + 1400 + 1500, выручка 2110, прибыль 2400 (docs/09 §2)."""
    g = c["girbo"]
    equity, long_term = round(g["assets"] * 0.4), round(g["assets"] * 0.2)
    return [{"period": "2025", "actualBfoDate": "2026-03-27", "typeCorrections": [{"correction": {
        "balance": {"current1600": g["assets"], "current1300": equity, "current1400": long_term,
                    "current1500": g["assets"] - equity - long_term},
        "financialResult": {"current2110": g["revenue"], "current2400": g["profit"]}}}]}]


def bki(c: dict, today: date) -> dict:
    """Кредитный отчёт: поля из формата ЦБ «Кредитный отчёт» v3.4 в JSON-зеркале (docs/09 §2)."""
    items = [{"DateOfConclusion": _months_ago(today, k["paid"], 14), "Amount": f"{k['amount']:.2f}", "CurrentLimit": "0.00",
              "PrincipalDebt": f"{k['debt']:.2f}", "OverdueAmount": "0.00", "PastdueDate": None,
              "PastDepthOfDelayInDay": k["overdue"], "AvgMonthPaymentSum": f"{k['payment']:.2f}",
              "TwoPaymentsSkipped": False, "LastPaymentDate": _months_ago(today, 1, 15) if k["paid"] else None}
             for k in credits(c)]
    kind = "CreditReportOfLegalPerson" if is_ul(c) else "CreditReportOfNaturalPerson"
    bankrupt = None
    if "bankruptcy" in c.get("flags", []):
        bankrupt = {"BRDate": _months_ago(today, 1, 10), "BankruptcyStage": "наблюдение"}
    return {kind: {"Subject": {"Identity": {"INN": c["inn"]}, "Bankruptcy": bankrupt},
                   "Credits": {"Credit": items}, "RequestsStatistic": {"NumberOfRequests": c["bki"]["requests"]}}}


def _default_outflows(c: dict) -> list:
    avg = sum(c["inflows"]) / 12
    rows = [["Зарплата, первая половина", 10, 0.12 * avg, "salary"], ["Зарплата, вторая половина", 25, 0.12 * avg, "salary"],
            ["Аренда", 25, 0.06 * avg, "rent"], ["Налоги и страховые взносы", 28, 0.08 * avg, "taxes"]]
    rows += [[f"Оплата поставщикам, неделя {w}", d, 0.09 * avg, "suppliers"] for w, d in enumerate((6, 13, 20, 27), 1)]
    return [[p, d, round(a, -3), cat] for p, d, a, cat in rows]


def _signed(t: dict) -> Decimal:
    return Decimal(t["amount"]) if t["direction"] == "in" else -Decimal(t["amount"])


def _month_flows(c: dict, today: date, rng: random.Random) -> list[tuple[int, int, int, list[dict]]]:
    """Поступления и регулярные платежи по месяцам: 12 полных и текущий до вчерашнего дня."""
    months = [divmod(today.year * 12 + today.month - 1 - back, 12) for back in range(12, -1, -1)]
    loans = sum(k["payment"] for k in credits(c))
    outflows = (c.get("outflows") or _default_outflows(c)) + ([["Платежи по кредитам", 15, loans, "loan_payment"]] * bool(loans))
    out = []
    for i, (y, m0) in enumerate(months):
        m, items = m0 + 1, []
        last_day = calendar.monthrange(y, m)[1] if i < 12 else today.day - 1
        total = c["inflows"][i] if i < 12 else int(sum(c["inflows"][-3:]) / 3 * last_day / 30 * 0.85)
        channel, payers = c.get("channel") or ("cards" if c.get("retail") else None), None
        if channel == "cards":                     # розница и общепит: эквайринг каждый день
            days = list(range(1, last_day + 1))
            purpose, counterparty, category = "Возмещение по операциям эквайринга", None, "acquiring"
        elif channel == "marketplace":             # маркетплейс платит раз в неделю
            days = list(range(3, last_day + 1, 7))
            purpose, counterparty, category = f"Выплата маркетплейса {MARKETPLACE[0]} за проданные товары", MARKETPLACE[1], \
                "marketplace"
        else:
            days = sorted(rng.sample(range(1, last_day + 1), min(last_day, rng.randint(5, 8))))
            purpose, counterparty, category = "Оплата по договору поставки", "7700000000", "customer_payment"
            payers = c.get("customers") if channel in ("invoices", "government") else None   # свои: несколько заказчиков
        weights = [rng.uniform(0.6, 1.4) for _ in days]
        parts = [int(total * w / sum(weights)) for w in weights]
        parts[-1] += total - sum(parts)
        for n, (day, amount) in enumerate(zip(days, parts, strict=True)):
            item = {"bookingDate": f"{y}-{m:02d}-{day:02d}", "amount": f"{amount:.2f}", "direction": "in",
                    "counterpartyInn": counterparty, "purpose": purpose, "category": category}
            if payers:
                name, inn = payers[(day + n) % len(payers)]
                what = "по акту выполненных работ по контракту" if channel == "government" \
                    else f"№ {m * 40 + day} за товары и услуги"
                item.update(counterpartyInn=inn, counterpartyName=name, purpose=f"Оплата по счёту {what}")
            items.append(item)
        for purpose_out, day, amount, category_out in outflows:
            if day <= last_day:
                items.append({"bookingDate": f"{y}-{m:02d}-{day:02d}", "amount": f"{amount:.2f}", "direction": "out",
                              "counterpartyInn": None, "purpose": purpose_out, "category": category_out})
        items.sort(key=lambda t: (t["bookingDate"], t["direction"]))       # в один день приход раньше расхода
        out.append((y, m, last_day, items))
    return out


def _dip(items: list[dict]) -> Decimal:
    """Насколько глубоко уходит остаток внутри месяца относительно его начала."""
    running, low = Decimal(0), Decimal(0)
    for t in items:
        running += _signed(t)
        low = min(low, running)
    return low


def _own_funds(c: dict, booking_date: str, amount: Decimal, *, back: bool) -> dict:
    """Свои деньги, не выручка: излишек — на депозит (у ИП — на личный счёт), нехватка — обратно или из своих."""
    ul = is_ul(c)
    if back:
        purpose = "Возврат депозита на расчётный счёт" if ul else "Пополнение счёта предпринимателем"
    else:
        purpose = "Размещение свободного остатка на депозите" if ul else "Перевод на личный счёт предпринимателя"
    return {"bookingDate": booking_date, "amount": f"{amount:.2f}", "direction": "in" if back else "out",
            "counterpartyInn": None, "purpose": purpose, "category": "deposit" if ul else "own_transfer"}


def _walk(c: dict, items: list[dict], start: Decimal, *, top_up: bool) -> tuple[list[dict], Decimal]:
    """Остаток по операциям; не хватает на платёж — в тот же день пополнение своими деньгами (счёт без овердрафта)."""
    out, running = [], start
    for t in items:
        if top_up and t["direction"] == "out" and running < Decimal(t["amount"]):
            need = Decimal(t["amount"]) - running
            refill = (need / 10_000).to_integral_value(rounding="ROUND_CEILING") * 10_000
            out.append(_own_funds(c, t["bookingDate"], refill, back=True))
            running += refill
        running += _signed(t)
        out.append(t)
    return out, running


def transactions(c: dict, today: date) -> dict:
    """Выписка, которая сходится: входящий остаток + приход − расход = сегодняшний, без ухода в минус без овердрафта.

    Поступления в сумме дают ровно inflows, регулярные платежи — по описанию, платежи по кредитам — из БКИ.
    Не хватает на платёж — в тот же день пополнение своими деньгами; в конце месяца остаток возвращается к одному
    уровню (излишек — на депозит или личный счёт ИП). Уровень подбирается так, чтобы остаток сегодня был равен balance
    из описания; если balance не задан (своя персона) — минимальный, при котором текущий месяц проходит без пополнений.
    """
    rng = random.Random(int(c["inn"]))
    months = _month_flows(c, today, rng)
    current = months[-1][3]
    current_net = sum((_signed(t) for t in current), Decimal(0))
    if c.get("balance") is not None:
        level = Decimal(c["balance"]) - current_net
    else:
        level = max(-_dip(current), Decimal(0)) + Decimal(round(sum(c["inflows"]) / 12 * 0.1, -3))
    items, running = [], level
    for i, (y, m, last_day, month_items) in enumerate(months):
        walked, running = _walk(c, month_items, running, top_up=i < 12)
        items += walked
        if i < 12 and running != level:
            items.append(_own_funds(c, f"{y}-{m:02d}-{last_day:02d}", abs(running - level), back=running < level))
            running = level
    balance = level
    for t in items:
        balance += _signed(t)
        t["balanceAfter"] = f"{balance:.2f}"
    return {"accountInn": c["inn"], "account": account(c["inn"]), "bik": BIK, "currency": "RUB",
            "openingBalance": {"amount": f"{level:.2f}", "asOf": items[0]["bookingDate"] if items else today.isoformat()},
            "balance": {"amount": f"{balance:.2f}", "asOf": today.isoformat()}, "items": items}


def payloads(c: dict, people: dict, today: date) -> dict:
    """Ответы всех источников по компании: {источник из policy/sources.yaml: тело}."""
    out = {}
    if is_ul(c):
        out["egrul"] = egrul(c, people, today)
        out["girbo"] = girbo(c)
        out["bank_charter"] = {"companyInn": c["inn"], "decisionMethod": c["charter"]["decisionMethod"], "limits": []}
    else:
        out["egrip"] = egrip(c, people)
    out.update(fns(c, people))
    bankrupt = "bankruptcy" in c.get("flags", [])
    out["legal"] = {"inn": c["inn"], "bankruptcy": {"stage": "наблюдение" if bankrupt else None,
                                                    "efrsbDate": _months_ago(today, 1, 10) if bankrupt else None},
                    "arbitration": {"asDefendantCount": 0, "claimsSum": "0.00"},
                    "enforcement": {"count": 0, "sum": "0.00"}, "sanctionsListHit": False}
    director = c.get("kyc_director") or (c["eio"][0][0] if is_ul(c) else c["owner"])
    out["bank_access"] = {"companyInn": c["inn"], "kycDirectorInn": people[director]["inn"],
                          "kycDirectorFio": " ".join(people[director]["fio"]), "persons": [
        {"personInn": people[p]["inn"], "fio": " ".join(people[p]["fio"]), "level": level} for p, level in c["access"]]}
    out["bank_tx"] = transactions(c, today)
    out["bki"] = bki(c, today)
    out["bki_info"] = {"subject": {"inn": c["inn"]}, "requests": {"last30days": c["bki"]["requests"]},
                       "refusals": {"last30days": 0}}
    if c.get("eis"):
        out["eis"] = {"contracts": [{**k, "price": f"{k['price']:.2f}", "treasurySupport": False} for k in c["eis"]]}
    if c.get("poa"):
        out["mchd"] = {"items": [mchd(c, poa, people) for poa in c["poa"]]}
    return out


def mchd(c: dict, poa: dict, people: dict) -> dict:
    """Машиночитаемая доверенность в формате публичного реестра ФНС (m4d): статус, доверитель, представитель, полномочия."""
    person = people[poa["person"]]
    guid = str(uuid.uuid5(uuid.NAMESPACE_OID, f"mchd:{c['inn']}:{person['inn']}"))
    return {"guid": guid, "status": poa["status"], "principal": {"inn": c["inn"], "ogrn": c["ogrn"]},
            "representative": {"inn": person["inn"], "snils": snils(person["inn"][1:10]), "fio": " ".join(person["fio"])},
            "powers": [{"code": code, "name": POWERS[code]} for code in poa["powers"]],
            "validFrom": poa["valid_from"], "validTo": poa["valid_to"]}


def registry_roles(c: dict, key: str) -> list[str]:
    """Кем человек записан в реестре: ИП, руководитель, участник."""
    roles = ["owner"] * (c.get("owner") == key)
    roles += ["eio"] * any(p == key for p, _ in c.get("eio", []))
    roles += ["participant"] * any(p == key for p, _ in c.get("participants", []))
    return roles


def person_card(key: str, person: dict, companies: list[dict]) -> dict:
    """Карточка клиента-физлица в банке: KYC и связи с компаниями — доступ в ДБО (уровень) и роли по реестру.
    Руководителей и участников с долей банк знает и без ДБО: их он идентифицирует по 115-ФЗ ст. 7."""
    links = []
    for c in companies:
        level = next((lvl for p, lvl in c["access"] if p == key), None)
        roles = registry_roles(c, key)
        if level or roles:
            links.append({"companyInn": c["inn"], "level": level or "registry", "roles": roles})
    return {"personInn": person["inn"], "fio": " ".join(person["fio"]), "snils": snils(person["inn"][1:10]),
            "kycStatus": "VERIFIED", "key": key, "companies": links}


def girbo_search(c: dict) -> dict:
    """Поиск организации в ГИР БО: реальный адаптер сначала ищет id по ИНН, потом берёт отчётность."""
    return {"content": [{"id": c["inn"], "inn": c["inn"], "ogrn": c["ogrn"], "shortName": c["name"]}]}


def served(c: dict, people: dict, today: date) -> dict:
    """То же, что payloads, но в точности как тело отдаст WireMock: через JSON, деньги — строками."""
    return json.loads(json.dumps(payloads(c, people, today), ensure_ascii=False, default=str))


# ── «своя персона»: компания из краткого описания ─────────────────────────────────────────────────────────────────
# Отрасли, профили и сезонность — допущения генератора симулятора (порядок величин, не статистика): из них строятся
# выписка, отчётность и люди своей компании. Числа, которые влияют на решение, считает движок из этих данных, как в бою.

_LAST = ("Соколов", "Морозов", "Волков", "Лебедев", "Козлов", "Новиков", "Павлов", "Семёнов", "Голубев", "Виноградов",
         "Богданов", "Воробьёв", "Фёдоров", "Михайлов", "Беляев", "Тарасов", "Комаров", "Киселёв", "Медведев", "Ершов")
_FIRST = {"m": ("Алексей", "Дмитрий", "Сергей", "Андрей", "Максим", "Илья", "Роман", "Михаил", "Николай", "Олег", "Павел",
                "Егор"),
          "f": ("Анна", "Мария", "Елена", "Ольга", "Наталья", "Ирина", "Татьяна", "Светлана", "Юлия", "Екатерина", "Дарья",
                "Виктория")}
_PATRONYMIC = {"m": ("Александрович", "Сергеевич", "Дмитриевич", "Андреевич", "Игоревич", "Владимирович", "Олегович"),
               "f": ("Александровна", "Сергеевна", "Дмитриевна", "Андреевна", "Игоревна", "Владимировна", "Олеговна")}
_CUSTOMERS = ("ООО «ТехноСнаб»", "ООО «Городской рынок»", "АО «СеверСтрой»", "ООО «Ритейл Плюс»", "ООО «Восток-Логистик»",
              "ООО «Профторг»", "ООО «Меридиан»", "ООО «СтройИнвест»", "ООО «Альтаир»", "ООО «Гранд Сервис»")
_SUPPLIERS = ("ООО «ПромСырьё»", "ООО «ТоргОпт»", "ООО «Упаковка-М»", "ООО «Техноресурс»", "ООО «ЛогистикПро»",
              "ООО «Агроснаб»", "ООО «Мельница»", "ООО «Офис-Комплект»")
# отрасль конструктора → ОКВЭД и профиль
INDUSTRIES = {
    "coffee": ("56.30", "Подача напитков", "horeca"),
    "restaurant": ("56.10", "Деятельность ресторанов и услуги по доставке продуктов питания", "horeca"),
    "bakery": ("10.71", "Производство хлеба и мучных кондитерских изделий, тортов и пирожных недлительного хранения",
               "manufacturing"),
    "retail_food": ("47.11", "Торговля розничная преимущественно пищевыми продуктами в неспециализированных магазинах",
                    "retail"),
    "online_shop": ("47.91", "Торговля розничная по почте или по информационно-коммуникационной сети Интернет", "marketplace"),
    "wholesale": ("46.90", "Торговля оптовая неспециализированная", "wholesale"),
    "construction": ("41.20", "Строительство жилых и нежилых зданий", "construction"),
    "renovation": ("43.39", "Производство прочих отделочных и завершающих работ", "construction"),
    "it": ("62.01", "Разработка компьютерного программного обеспечения", "it"),
    "trucking": ("49.41", "Деятельность автомобильного грузового транспорта", "logistics"),
    "warehouse": ("52.10", "Деятельность по складированию и хранению", "logistics"),
    "farm": ("01.11", "Выращивание зерновых (кроме риса), зернобобовых культур и семян масличных культур", "farm"),
    "cleaning": ("81.21", "Деятельность по общей уборке зданий", "services"),
    "beauty": ("96.02", "Предоставление услуг парикмахерскими и салонами красоты", "services_retail"),
    "dental": ("86.23", "Стоматологическая практика", "services_retail"),
    "education": ("85.41", "Образование дополнительное детей и взрослых", "services"),
}
# отрасль конструктора → коротко и по-человечески (экран входа, конструктор, профиль)
INDUSTRY_TITLES = {
    "coffee": ("Кофейня", "Coffee shop"), "restaurant": ("Ресторан или доставка еды", "Restaurant or food delivery"),
    "bakery": ("Пекарня, хлебозавод", "Bakery"), "retail_food": ("Продуктовый магазин", "Grocery store"),
    "online_shop": ("Интернет-магазин на маркетплейсах", "Online shop on marketplaces"),
    "wholesale": ("Оптовая торговля", "Wholesale"), "construction": ("Строительство", "Construction"),
    "renovation": ("Ремонт и отделка", "Renovation"), "it": ("Разработка программ", "Software development"),
    "trucking": ("Грузоперевозки", "Trucking"), "warehouse": ("Склад и логистика", "Warehousing"),
    "farm": ("Сельское хозяйство", "Farming"), "cleaning": ("Клининг", "Cleaning"), "beauty": ("Салон красоты", "Beauty salon"),
    "dental": ("Стоматология", "Dental clinic"), "education": ("Курсы и обучение", "Courses and training"),
}
_SECTION_TITLES = {   # ОКВЭД без отрасли в каталоге → по первым двум цифрам
    "01": ("Сельское хозяйство", "Farming"), "10": ("Производство еды", "Food production"),
    "41": ("Строительство", "Construction"), "43": ("Ремонт и отделка", "Renovation"), "46": ("Оптовая торговля", "Wholesale"),
    "47": ("Розничная торговля", "Retail"), "49": ("Грузоперевозки", "Trucking"), "52": ("Склад и логистика", "Warehousing"),
    "56": ("Общепит", "Food service"), "62": ("Разработка программ", "Software development"), "81": ("Клининг", "Cleaning"),
    "85": ("Обучение", "Education"), "86": ("Медицина", "Healthcare"), "96": ("Бытовые услуги", "Personal services"),
}


def industry_title(okved: str | None, lang: str = "ru") -> str | None:
    """Вид деятельности коротко: «Пекарня, хлебозавод», а не формулировка ОКВЭД; нет в каталоге — None."""
    if not okved:
        return None
    i = 0 if lang == "ru" else 1
    exact = next((INDUSTRY_TITLES[k][i] for k, (code, _, _) in INDUSTRIES.items() if code == okved), None)
    return exact or (_SECTION_TITLES.get(okved[:2]) or (None, None))[i]


# профиль: сезонность и канал по умолчанию, доли регулярных платежей от средних поступлений, маржа, активы / выручка
PROFILES = {
    "horeca": {"season": "summer", "channel": "cards", "payroll": .30, "rent": .12, "suppliers": .30, "taxes": .07,
               "other": .05, "margin": .06, "assets": .35},
    "manufacturing": {"season": "flat", "channel": "invoices", "payroll": .25, "rent": .05, "suppliers": .45, "taxes": .07,
                      "other": .06, "margin": .05, "assets": .7},
    "retail": {"season": "year_end", "channel": "cards", "payroll": .14, "rent": .10, "suppliers": .58, "taxes": .05,
               "other": .04, "margin": .03, "assets": .5},
    "marketplace": {"season": "year_end", "channel": "marketplace", "payroll": .10, "rent": .05, "suppliers": .60,
                    "taxes": .05, "other": .08, "margin": .05, "assets": .4},
    "wholesale": {"season": "flat", "channel": "invoices", "payroll": .07, "rent": .04, "suppliers": .75, "taxes": .04,
                  "other": .03, "margin": .03, "assets": .45},
    "construction": {"season": "summer", "channel": "invoices", "payroll": .30, "rent": .03, "suppliers": .45, "taxes": .07,
                     "other": .05, "margin": .05, "assets": .8},
    "it": {"season": "flat", "channel": "invoices", "payroll": .55, "rent": .06, "suppliers": .07, "taxes": .10, "other": .07,
           "margin": .12, "assets": .3},
    "logistics": {"season": "flat", "channel": "invoices", "payroll": .30, "rent": .08, "suppliers": .35, "taxes": .07,
                  "other": .08, "margin": .05, "assets": .9},
    "farm": {"season": "harvest", "channel": "invoices", "payroll": .20, "rent": .05, "suppliers": .45, "taxes": .03,
             "other": .07, "margin": .08, "assets": 1.2},
    "services": {"season": "flat", "channel": "invoices", "payroll": .55, "rent": .04, "suppliers": .15, "taxes": .08,
                 "other": .05, "margin": .07, "assets": .25},
    "services_retail": {"season": "flat", "channel": "cards", "payroll": .40, "rent": .15, "suppliers": .15, "taxes": .07,
                        "other": .05, "margin": .08, "assets": .3},
}
SEASONS = {   # множитель месяца, январь…декабрь: лето у общепита и стройки, конец года у розницы, урожай у аграриев
    "flat": (1,) * 12,
    "summer": (0.78, 0.8, 0.9, 1.0, 1.1, 1.25, 1.3, 1.25, 1.05, 0.95, 0.82, 0.8),
    "year_end": (0.8, 0.85, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 1.0, 1.05, 1.15, 1.45),
    "harvest": (0.4, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0, 1.4, 2.0, 2.0, 1.4, 0.85),
}
NOISE = {"steady": 0.04, "uneven": 0.15, "volatile": 0.35}       # как сильно месяц отличается от сезонного
MARKETPLACE = ("ООО «Онлайн Маркет»", "7718990011")              # условная площадка, ИНН с верной контрольной цифрой
GOVERNMENT = ("ГБУ «Городской заказчик № 7»", "7718990029")
STRUCTURES = ("owner_director", "hired_director", "partners", "two_directors_joint", "two_directors_independent")
_PROFILE_BY_SECTION = {"A": "farm", "C": "manufacturing", "F": "construction", "H": "logistics", "I": "horeca", "J": "it"}


def profile_for(okved: str) -> str:
    """Отрасль не из каталога — профиль по разделу ОКВЭД; торговля: 46 — опт, 47 — розница."""
    if okved.startswith("46"):
        return "wholesale"
    if okved.startswith("47"):
        return "retail"
    return _PROFILE_BY_SECTION.get(section_of(okved) or "", "services")


def _name(number: int, i: int, used: set[str]) -> list[str]:
    """ФИО человека своей компании: детерминированно по номеру, пол согласован, фамилии в компании не повторяются."""
    rng = random.Random(number * 97 + i)
    sex = "f" if rng.random() < 0.45 else "m"
    last = next(x for x in rng.sample(_LAST, len(_LAST)) if x not in used)
    used.add(last)
    return [last + ("а" if sex == "f" else ""), rng.choice(_FIRST[sex]), rng.choice(_PATRONYMIC[sex])]


def _shares(n: int) -> list[int]:
    """Доли участников неравные, как в жизни: 60/40, 40/35/25, 40/25/20/15…; сумма — 100%."""
    fixed = {1: [100], 2: [60, 40], 3: [40, 35, 25], 4: [40, 25, 20, 15], 5: [35, 25, 20, 12, 8]}
    if n in fixed:
        return fixed[n]
    raw = [n - i for i in range(n)]
    shares = [int(100 * r / sum(raw)) for r in raw]
    shares[0] += 100 - sum(shares)
    return shares


def _seasonal(avg: float, season: str, noise: float, trend: float, today: date, number: int) -> list[int]:
    """12 полных месяцев до сегодня: сезонный профиль отрасли, разброс и тренд последних трёх месяцев; среднее — avg."""
    shape = SEASONS[season]
    mean = sum(shape) / 12
    rng = random.Random(number * 13 + 7)
    months = [divmod(today.year * 12 + today.month - 1 - back, 12)[1] for back in range(12, 0, -1)]
    values = [shape[m] / mean * (1 + rng.uniform(-noise, noise)) * (1 + trend if i >= 9 else 1) for i, m in enumerate(months)]
    scale = avg * 12 / sum(values)
    return [max(10_000, round(v * scale, -3)) for v in values]


def _profile_outflows(avg: float, p: dict, suppliers: list[list]) -> list:
    """Регулярные платежи из профиля: зарплата дважды в месяц (ТК ст. 136 ч. 6), аренда, единый налоговый платёж,
    коммунальные и связь, поставщики по счетам раз в неделю."""
    rows = [["Заработная плата за первую половину месяца", 10, p["payroll"] / 2 * avg, "salary"],
            ["Заработная плата за вторую половину месяца", 25, p["payroll"] / 2 * avg, "salary"],
            ["Аренда помещения по договору", 5, p["rent"] * avg, "rent"],
            ["Единый налоговый платёж", 28, p["taxes"] * avg, "taxes"],
            ["Коммунальные услуги и связь", 15, p["other"] * avg, "utilities"]]
    rows += [[f"Оплата по счёту поставщику {suppliers[k % len(suppliers)][0]}", day, p["suppliers"] / 4 * avg, "suppliers"]
             for k, day in enumerate((7, 14, 21, 27))]
    return [[purpose, day, round(amount, -3), cat] for purpose, day, amount, cat in rows if round(amount, -3) > 0]


def _companies(pool: tuple, number: int, k: int, prefix: str) -> list[list]:
    """Контрагенты своей компании: название и ИНН с верной контрольной цифрой (не пересекаются с миром)."""
    rng = random.Random(number * 7 + len(prefix))
    return [[name, inn_ul(f"{prefix}{(number * 10 + i) % 100000:05d}")] for i, name in enumerate(rng.sample(pool, k))]


def _series(avg: float, cv: float, trend: float) -> list[int]:
    """12 месяцев со средним avg, разбросом около cv и трендом: последние 3 к предыдущим 9 = 1 + trend."""
    m9 = 12 * avg / (12 + 3 * trend)
    m3 = m9 * (1 + trend)
    shape9, shape3 = (1, -1, 1, -1, 0, 1, -1, 1, -1), (1, -1, 0)
    values = [m9 * (1 + cv * s) for s in shape9] + [m3 * (1 + cv * s) for s in shape3]
    return [max(1000, round(v, -3)) for v in values]


def custom(spec: dict, number: int, today: date) -> tuple[dict, dict]:
    """Компания и люди из краткого описания — для симулятора («своя компания») и pairwise-тестов.

    spec: kind (IP | LLC | JSC), okved [код, название], age_months, headcount, inflow_avg, debt_load, overdue_days,
    bki_requests, tax_debt, participants (число), flags, contract_price, assets_share (активы / годовая выручка — от него
    порог крупной сделки), profit_margin, owner_fio [фамилия, имя, отчество], company_name (без ОПФ) и inn.
    Как устроена компания — structure: owner_director · hired_director · partners · two_directors_joint ·
    two_directors_independent, плюс accountant (бухгалтер с подготовкой в ДБО) и representative (представитель по МЧД).
    Простым языком — profile (отрасль, PROFILES), seasonality (SEASONS), stability (NOISE), channel (cards · invoices ·
    marketplace · government): из них выписка с сезонностью, контрагенты, регулярные платежи и отчётность.
    inflow_cv задан явно (флаг «нестабильные поступления», pairwise) — поступления по нему, без сезонности.
    ИНН, ОГРН и люди генерируются детерминированно по number.
    """
    kind = spec.get("kind", "LLC")
    profile = PROFILES.get(spec.get("profile") or "")
    reg_year, reg_month = divmod(today.year * 12 + today.month - 1 - spec.get("age_months", 36), 12)
    registered = f"{reg_year}-{reg_month + 1:02d}-05"
    structure = "owner" if kind == "IP" else spec.get("structure") or (
        "partners" if spec.get("participants", 1) > 1 else "owner_director")
    shared = structure in ("partners", "two_directors_joint", "two_directors_independent")
    n_partners = max(2, spec.get("participants", 2)) if shared else 1

    people, used = {}, set()

    def person() -> str:
        key = f"p{number}_{len(people)}"
        people[key] = {"fio": _name(number, len(people), used), "inn": inn_fl(f"7705{number:04d}{len(people):02d}")}
        return key

    partners = [person() for _ in range(n_partners)]                 # первый — владелец: ИП или участник
    directors = [person()] if structure == "hired_director" else partners[:2] if structure.startswith("two_") \
        else partners[:1]
    main = directors[0]                                               # кто входит в кабинет: руководитель (у ИП — он сам)
    accountant = person() if spec.get("accountant") else None
    representative = person() if spec.get("representative") and kind != "IP" else None
    if spec.get("owner_fio"):
        people[main]["fio"] = list(spec["owner_fio"])

    avg = spec.get("inflow_avg", 3_000_000)
    if "inflow_cv" in spec or not (profile or spec.get("seasonality") or spec.get("stability")):
        inflows = _series(avg, spec.get("inflow_cv", 0.3), spec.get("inflow_trend", 0.0))
    else:
        inflows = _seasonal(avg, spec.get("seasonality") or (profile or PROFILES["services"])["season"],
                            NOISE[spec.get("stability") or "uneven"], spec.get("inflow_trend", 0.0), today, number)
    payment = spec.get("debt_load", 0.15) * avg
    factor = float(annuity_payment(1_000_000, 20, 36)) / 1_000_000              # платёж на рубль долга: 20% на 36 мес.
    loan = [] if payment <= 0 else [[max(100_000, round(payment / factor, -5)), 20, 36, 10, spec.get("overdue_days", 0)]]
    title = spec.get("company_name") or f"{industry_title((spec.get('okved') or [''])[0]) or 'Своё дело'} {number % 1000}"
    revenue = round(sum(inflows) / 1000)
    small = (msp_category(spec.get("headcount", 12), revenue * 1000) or 3) <= 2
    regime = spec.get("tax_regime") or ("ESHN" if profile is PROFILES["farm"] else "USN" if kind == "IP" or small else "OSN")
    c = {"key": f"custom{number}", "name": f"{'АО' if kind == 'JSC' else 'ООО'} «{title}»",
         "registered": registered, "okved": spec.get("okved", ["62.01", "Разработка компьютерного программного обеспечения"]),
         "headcount": spec.get("headcount", 12), "tax": {"regime": regime, "debt": spec.get("tax_debt", 0)},
         "inflows": inflows, "bki": {"credits": loan, "requests": spec.get("bki_requests", 1)},
         "flags": spec.get("flags", []), "titles": {}}
    if profile:                                       # выписка как у отрасли: контрагенты, канал оплат, регулярные платежи
        suppliers, channel = _companies(_SUPPLIERS, number, 3, "7719"), spec.get("channel") or profile["channel"]
        customers = [list(GOVERNMENT)] if channel == "government" else _companies(_CUSTOMERS, number, 4, "7718")
        c.update(channel=channel, customers=customers, suppliers=suppliers,
                 outflows=_profile_outflows(avg, profile, suppliers))
    if kind == "IP":
        owner = partners[0]
        c.update(inn=spec.get("inn") or inn_fl(f"7706{number:06d}"), owner=owner, access=[[owner, "owner"]])
        c["name"] = "ИП " + " ".join(part for part in people[owner]["fio"] if part)
        people[owner]["inn"] = c["inn"]                                          # ИНН ИП = ИНН человека
    else:
        margin, assets = (profile or {}).get("margin", 0.05), (profile or {}).get("assets", 0.6)
        c.update(inn=spec.get("inn") or inn_ul(f"7707{number:05d}"), opf="JSC" if kind == "JSC" else "LLC",
                 eio=[[d, "Генеральный директор" if i == 0 else "Директор"] for i, d in enumerate(directors)],
                 eio_mode="joint" if structure == "two_directors_joint" else "independent",
                 participants=[] if kind == "JSC" else [[k, s] for k, s in zip(partners, _shares(len(partners)),
                                                                               strict=True)],
                 charter={"decisionMethod": "protocol"},
                 access=[[d, "owner"] for d in directors]       # владелец при наёмном директоре видит счёт в ДБО
                 + [[partners[0], "view"]] * (structure == "hired_director"),
                 girbo={"assets": round(revenue * spec.get("assets_share", assets)), "revenue": revenue,
                        "profit": round(revenue * spec.get("profit_margin", margin))})
        if structure == "hired_director":
            c["titles"][partners[0]] = "Владелец"
    if accountant:
        c["access"].append([accountant, "prepare"])
        c["titles"][accountant] = "Главный бухгалтер"
    if representative:                                  # МЧД с правом подписать кредитный договор (ГК ст. 185.1)
        c["access"].append([representative, "prepare"])
        c["titles"][representative] = "Финансовый директор"
        c["poa"] = [{"person": representative, "status": "ACTIVE", "powers": ["CREDIT_AGREEMENT_SIGN"],
                     "valid_from": _months_ago(today, 3, 1), "valid_to": _months_ago(today, -12, 28)}]
    c["ogrn"] = ogrn(reg_year, c["inn"][:2], number, ip=kind == "IP")
    if spec.get("contract_price"):
        c["eis"] = [{"regNum": f"27707{number:014d}", "customer": "ГБУ «Городской заказчик № 7»",
                     "price": spec["contract_price"], "signDate": _months_ago(today, 1, 10),
                     "endDate": _months_ago(today, -8, 28), "advancePercent": 20}]
    return c, people
