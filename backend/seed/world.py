"""Демо-мир: из описания компании — ответы всех внешних источников в форматах docs/09.

Чистые функции без записи на диск. Генератор моков пишет их в wiremock/, песочница ставит в WireMock на лету
(«своя персона»), тесты строят мир в памяти. validate() — правила корректности: контрольные цифры, даты,
согласованность источников между собой. Платежи по кредитам, категория МСП и платежи в выписке банка
не задаются руками, а выводятся, поэтому разойтись не могут.
"""

import calendar
import json
import random
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
    "bank_charter": "bank/charter", "bank_tx": "bank/tx", "eis": "eis", "bki": "bki", "bki_info": "bki-info",
}
OPF = {"LLC": ("12300", "Общество с ограниченной ответственностью"),
       "JSC": ("12267", "Непубличное акционерное общество")}
# 209-ФЗ ст. 4: численность ≤ 15 / 100 / 250 чел., доход ≤ 120 млн / 800 млн / 2 млрд ₽ (ПП РФ № 265; docs/10 L9, L10).
# Категория — по большему из двух показателей.
MSP_LIMITS = ((1, 15, 120_000_000), (2, 100, 800_000_000), (3, 250, 2_000_000_000))
FLAGS = {"liquidation", "bankruptcy", "unreliable_eio", "disqualified_eio"}
UL_ONLY_FLAGS = {"liquidation", "unreliable_eio", "disqualified_eio"}     # отметки ЕГРЮЛ; в ЕГРИП их нет
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
          "СвОКВЭД": _okved(c), "СвПолном": {"@ВидПолном": "2"}, "СведДолжнФЛ": directors,
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


def transactions(c: dict, today: date) -> dict:
    """Операции по счёту: поступления в сумме дают ровно inflows; регулярные платежи и платежи по кредитам из БКИ."""
    rng = random.Random(int(c["inn"]))
    months = [divmod(today.year * 12 + today.month - 1 - back, 12) for back in range(12, -1, -1)]
    loans = sum(k["payment"] for k in credits(c))
    outflows = (c.get("outflows") or _default_outflows(c)) + ([["Платежи по кредитам", 15, loans, "loan_payment"]] * bool(loans))
    items = []
    for i, (y, m0) in enumerate(months):
        m = m0 + 1
        last_day = calendar.monthrange(y, m)[1] if i < 12 else today.day - 1
        total = c["inflows"][i] if i < 12 else int(sum(c["inflows"][-3:]) / 3 * last_day / 30 * 0.85)
        if c.get("retail"):
            days = list(range(1, last_day + 1))
            purpose, counterparty, category = "Возмещение по операциям эквайринга", None, "acquiring"
        else:
            days = sorted(rng.sample(range(1, last_day + 1), min(last_day, rng.randint(5, 8))))
            purpose, counterparty, category = "Оплата по договору поставки", "7700000000", "customer_payment"
        weights = [rng.uniform(0.6, 1.4) for _ in days]
        parts = [int(total * w / sum(weights)) for w in weights]
        parts[-1] += total - sum(parts)
        for day, amount in zip(days, parts, strict=True):
            items.append({"bookingDate": f"{y}-{m:02d}-{day:02d}", "amount": f"{amount:.2f}", "direction": "in",
                          "counterpartyInn": counterparty, "purpose": purpose, "category": category})
        for purpose_out, day, amount, category_out in outflows:
            if day <= last_day:
                items.append({"bookingDate": f"{y}-{m:02d}-{day:02d}", "amount": f"{amount:.2f}", "direction": "out",
                              "counterpartyInn": None, "purpose": purpose_out, "category": category_out})
    items.sort(key=lambda t: (t["bookingDate"], t["direction"]))
    return {"accountInn": c["inn"], "account": "40702810" + c["inn"][-10:].rjust(12, "0"), "currency": "RUB",
            "balance": {"amount": f"{c['balance']:.2f}", "asOf": today.isoformat()}, "items": items}


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
    out["bank_access"] = {"companyInn": c["inn"], "kycDirectorInn": people[director]["inn"], "persons": [
        {"personInn": people[p]["inn"], "fio": " ".join(people[p]["fio"]), "level": level} for p, level in c["access"]]}
    out["bank_tx"] = transactions(c, today)
    out["bki"] = bki(c, today)
    out["bki_info"] = {"subject": {"inn": c["inn"]}, "requests": {"last30days": c["bki"]["requests"]},
                       "refusals": {"last30days": 0}}
    if c.get("eis"):
        out["eis"] = {"contracts": [{**k, "price": f"{k['price']:.2f}", "treasurySupport": False} for k in c["eis"]]}
    return out


def person_card(key: str, person: dict) -> dict:
    """Карточка клиента-физлица в банке (KYC): по ней демо-пользователь входит как этот человек."""
    return {"personInn": person["inn"], "fio": " ".join(person["fio"]), "snils": snils(person["inn"][1:10]),
            "kycStatus": "VERIFIED", "key": key}


def girbo_search(c: dict) -> dict:
    """Поиск организации в ГИР БО: реальный адаптер сначала ищет id по ИНН, потом берёт отчётность."""
    return {"content": [{"id": c["inn"], "inn": c["inn"], "ogrn": c["ogrn"], "shortName": c["name"]}]}


def served(c: dict, people: dict, today: date) -> dict:
    """То же, что payloads, но в точности как тело отдаст WireMock: через JSON, деньги — строками."""
    return json.loads(json.dumps(payloads(c, people, today), ensure_ascii=False, default=str))


# ── «своя персона»: компания из краткого описания ─────────────────────────────────────────────────────────────────

_SURNAMES = ("Соколов", "Морозов", "Волков", "Зайцев", "Павлов", "Семёнов", "Голубев", "Виноградов", "Богданов", "Воробьёв")


def _series(avg: float, cv: float, trend: float) -> list[int]:
    """12 месяцев со средним avg, разбросом около cv и трендом: последние 3 к предыдущим 9 = 1 + trend."""
    m9 = 12 * avg / (12 + 3 * trend)
    m3 = m9 * (1 + trend)
    shape9, shape3 = (1, -1, 1, -1, 0, 1, -1, 1, -1), (1, -1, 0)
    values = [m9 * (1 + cv * s) for s in shape9] + [m3 * (1 + cv * s) for s in shape3]
    return [max(1000, round(v, -3)) for v in values]


def custom(spec: dict, number: int, today: date) -> tuple[dict, dict]:
    """Компания и люди из краткого описания — для песочницы («собрать свою персону») и pairwise-тестов.

    spec: kind (IP | LLC | JSC), okved [код, название], age_months, headcount, inflow_avg, inflow_cv, inflow_trend,
    debt_load, overdue_days, bki_requests, tax_debt, participants (число), profit_margin, flags, contract_price.
    ИНН, ОГРН и люди генерируются детерминированно по number.
    """
    kind = spec.get("kind", "LLC")
    reg_year, reg_month = divmod(today.year * 12 + today.month - 1 - spec.get("age_months", 36), 12)
    registered = f"{reg_year}-{reg_month + 1:02d}-05"
    head = _SURNAMES[number % len(_SURNAMES)]
    people = {f"p{number}_{i}": {"fio": [head if i == 0 else _SURNAMES[(number + i) % len(_SURNAMES)], "Иван", "Петрович"],
                                 "inn": inn_fl(f"7705{number:04d}{i:02d}")} for i in range(max(1, spec.get("participants", 1)))}
    keys = list(people)
    avg = spec.get("inflow_avg", 3_000_000)
    inflows = _series(avg, spec.get("inflow_cv", 0.3), spec.get("inflow_trend", 0.0))
    payment = spec.get("debt_load", 0.15) * avg
    factor = float(annuity_payment(1_000_000, 20, 36)) / 1_000_000              # платёж на рубль долга: 20% на 36 мес.
    loan = [] if payment <= 0 else [[max(100_000, round(payment / factor, -5)), 20, 36, 10, spec.get("overdue_days", 0)]]
    c = {"key": f"custom{number}", "name": f"{'ИП' if kind == 'IP' else 'ООО'} «Персона {number}»",
         "registered": registered, "okved": spec.get("okved", ["62.01", "Разработка компьютерного программного обеспечения"]),
         "headcount": spec.get("headcount", 12), "tax": {"regime": "OSN", "debt": spec.get("tax_debt", 0)},
         "inflows": inflows, "balance": round(avg * 0.3, -3), "bki": {"credits": loan, "requests": spec.get("bki_requests", 1)},
         "flags": spec.get("flags", [])}
    if kind == "IP":
        c.update(inn=inn_fl(f"7706{number:06d}"), owner=keys[0], access=[[keys[0], "owner"]])
        c["name"] = f"ИП {' '.join(people[keys[0]]['fio'])}"
        people[keys[0]]["inn"] = c["inn"]                                        # ИНН ИП = ИНН человека
    else:
        revenue = round(sum(inflows) / 1000)
        n = len(keys)
        shares = [100 // n + (1 if i < 100 % n else 0) for i in range(n)]
        c.update(inn=inn_ul(f"7707{number:05d}"), opf="JSC" if kind == "JSC" else "LLC", eio=[[keys[0], "Генеральный директор"]],
                 participants=[] if kind == "JSC" else [[k, s] for k, s in zip(keys, shares, strict=True)],
                 charter={"decisionMethod": "protocol"}, access=[[keys[0], "owner"]],
                 girbo={"assets": round(revenue * 0.6), "revenue": revenue,
                        "profit": round(revenue * spec.get("profit_margin", 0.05))})
        if kind == "JSC":
            c["name"] = c["name"].replace("ООО", "АО")
    c["ogrn"] = ogrn(reg_year, c["inn"][:2], number, ip=kind == "IP")
    if spec.get("contract_price"):
        c["eis"] = [{"regNum": f"27707{number:014d}", "customer": "ГБУ «Городской заказчик № 7»",
                     "price": spec["contract_price"], "signDate": _months_ago(today, 1, 10),
                     "endDate": _months_ago(today, -8, 28), "advancePercent": 20}]
    return c, people
