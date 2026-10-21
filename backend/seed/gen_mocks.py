"""Генератор моков WireMock из демо-мира: python seed/gen_mocks.py

seed/personas.yaml → wiremock/__files/<источник>/<ключ>.json (ответы в форматах docs/09) + wiremock/mappings/*.json
(по стабу на ручку: тело выбирается по ИНН шаблоном, неизвестный ИНН → 404). Руками JSON не пишем (docs/06 §12).
Детерминированно: тот же personas.yaml → те же файлы (CI сверяет git diff).
"""

import calendar
import json
import random
import shutil
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / "seed" / "personas.yaml"
OUT = ROOT / "wiremock"
JSON_HEADERS = {"Content-Type": "application/json; charset=utf-8"}
NOT_FOUND = {"status": 404, "headers": {"Content-Type": "application/problem+json"},
             "jsonBody": {"type": "about:blank", "title": "Not Found", "status": 404, "detail": "Запись не найдена"}}


def write(rel: str, obj) -> None:
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", "utf-8")


def fio(person: dict) -> dict:
    last, first, middle = person["fio"]
    return {"@Фамилия": last, "@Имя": first, "@Отчество": middle}


def okved(c: dict) -> dict:
    return {"СвОКВЭДОсн": {"@КодОКВЭД": c["okved"][0], "@НаимОКВЭД": c["okved"][1], "@ПрВерсОКВЭД": "2014"}}


def is_ul(c: dict) -> bool:
    return len(c["inn"]) == 10


# ── реестры ──────────────────────────────────────────────────────────────────────────────────────────────────────


def egrul(c: dict, people: dict) -> dict:
    """JSON-зеркало выписки ЕГРЮЛ, формат ФНС 4.06 (docs/09 §2)."""
    return {"СвЮЛ": {
        "@ОГРН": c["ogrn"], "@ДатаОГРН": c["registered"], "@ИНН": c["inn"], "@КПП": c["inn"][:4] + "01001",
        "@КодОПФ": c.get("opf", "12300"), "@ПолнНаимОПФ": "Общество с ограниченной ответственностью",
        "СвНаимЮЛ": {"@НаимЮЛПолн": c["name"].replace("ООО ", "ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "),
                     "@НаимЮЛСокр": c["name"]},
        "СвОКВЭД": okved(c),
        "СвПолном": {"@ВидПолном": "2"},                       # 2 — каждый ЕИО действует независимо
        "СведДолжнФЛ": [{"СвФЛ": {**fio(people[p]), "@ИННФЛ": people[p]["inn"]},
                         "СвДолжн": {"@ВидДолжн": "02", "@НаимДолжн": title}} for p, title in c["eio"]],
        "СвУчредит": {"УчрФЛ": [{"СвФЛ": {**fio(people[p]), "@ИННФЛ": people[p]["inn"]},
                                 "ДоляУстКап": {"@НоминСтоим": str(share * 100), "РазмерДоли": {"Процент": str(share)}}}
                                for p, share in c["participants"]]},
    }}


def egrip(c: dict, people: dict) -> dict:
    owner = people[c["owner"]]
    return {"СвИП": {"@ОГРНИП": c["ogrn"], "@ДатаОГРНИП": c["registered"], "@ИННФЛ": c["inn"], "@КодВидИП": "1",
                     "СвФЛ": {"ФИОРус": fio(owner)}, "СвОКВЭД": okved(c)}}


def fns(c: dict, people: dict) -> dict[str, dict]:
    ul, tax = is_ul(c), c.get("tax", {})
    who = {"ОргВклМСП": {"@НаимОрг": c["name"], "@ИННЮЛ": c["inn"]}} if ul else \
        {"ИПВклМСП": {"@ИННФЛ": c["inn"], "ФИОИП": fio(people[c["owner"]])}}
    debt = tax.get("debt", 0)
    debts = [] if not debt else [
        {"@НаимНалог": "Налог, взимаемый в связи с применением упрощённой системы налогообложения",
         "@СумНедНалог": f"{debt * 0.7:.2f}", "@СумПени": "0.00", "@СумШтраф": "0.00", "@ОбщСумНедоим": f"{debt * 0.7:.2f}"},
        {"@НаимНалог": "Страховые взносы на обязательное социальное страхование",
         "@СумНедНалог": f"{debt * 0.3:.2f}", "@СумПени": "0.00", "@СумШтраф": "0.00", "@ОбщСумНедоим": f"{debt * 0.3:.2f}"},
    ]
    regime = tax.get("regime", "OSN")
    yearly = sum(c["inflows"])
    return {
        "rsmp": {"Документ": {"@ДатаСост": "2026-10-10", "@ВидСубМСП": "1" if ul else "2", "@КатСубМСП": str(c["msp"]),
                              "@ДатаВклМСП": c["registered"], **who, "СвОКВЭД": okved(c)}},
        "sshr": {"Документ": {"@ДатаСост": "2025-12-31", "СведССЧР": {"@КолРаб": str(c["headcount"])}}},
        "paytax": {"Документ": {"@ДатаСост": "2025-12-31", "СвУплСумНал": [
            {"@НаимНалог": "Страховые взносы на обязательное пенсионное страхование", "@СумУплНал": f"{yearly * 0.03:.2f}"},
            {"@НаимНалог": "Налог на доходы физических лиц", "@СумУплНал": f"{yearly * 0.015:.2f}"}]}},
        "debtam": {"Документ": {"@ДатаСост": "2026-10-01", "СведНедоим": debts}},
        "snr": {"Документ": {"@ДатаСост": "2025-12-31", "СведСНР": {
            "@ПризнЕСХН": str(int(regime == "ESHN")), "@ПризнУСН": str(int(regime == "USN")),
            "@ПризнАУСН": str(int(regime == "AUSN")), "@ПризнСРП": "0"}}},
    }


def girbo(c: dict) -> list:
    """ГИР БО (bo.nalog.gov.ru): суммы в тыс. ₽, поля current1600 / 2110 / 2400 (docs/09 §2)."""
    g = c["girbo"]
    return [{"period": "2025", "actualBfoDate": "2026-03-27", "typeCorrections": [{"correction": {
        "balance": {"current1600": g["assets"], "current1300": round(g["assets"] * 0.4),
                    "current1400": round(g["assets"] * 0.2), "current1500": round(g["assets"] * 0.4)},
        "financialResult": {"current2110": g["revenue"], "current2400": g["profit"]}}}]}]


def bki(c: dict, today: date) -> dict:
    """Кредитный отчёт, формат ЦБ v3.4 в JSON-зеркале (docs/09 §2)."""
    credits = [{"DateOfConclusion": f"{today.year - 1}-0{3 + i}-14", "Amount": f"{amount:.2f}", "CurrentLimit": "0.00",
                "PrincipalDebt": f"{debt:.2f}", "OverdueAmount": "0.00", "PastdueDate": None,
                "PastDepthOfDelayInDay": overdue, "AvgMonthPaymentSum": f"{pay:.2f}", "TwoPaymentsSkipped": False,
                "LastPaymentDate": f"{today.year}-{today.month - 1:02d}-15"}
               for i, (amount, debt, pay, overdue) in enumerate(c["bki"]["credits"])]
    kind = "CreditReportOfLegalPerson" if is_ul(c) else "CreditReportOfNaturalPerson"
    return {kind: {"Subject": {"Identity": {"INN": c["inn"]}, "Bankruptcy": None},
                   "Credits": {"Credit": credits}, "RequestsStatistic": {"NumberOfRequests": c["bki"]["requests"]}}}


# ── банк ─────────────────────────────────────────────────────────────────────────────────────────────────────────


def default_outflows(c: dict) -> list:
    avg = sum(c["inflows"]) / 12
    loans = sum(pay for _, _, pay, _ in c["bki"]["credits"])
    rows = [["Зарплата, первая половина", 10, 0.12 * avg, "salary"], ["Зарплата, вторая половина", 25, 0.12 * avg, "salary"],
            ["Аренда", 25, 0.06 * avg, "rent"], ["Налоги и страховые взносы", 28, 0.08 * avg, "taxes"]]
    rows += [[f"Оплата поставщикам, неделя {w}", d, 0.09 * avg, "suppliers"] for w, d in enumerate((6, 13, 20, 27), 1)]
    if loans:
        rows.append(["Платежи по кредитам", 15, loans, "loan_payment"])
    return [[p, d, round(a, -3), cat] for p, d, a, cat in rows]


def months_back(today: date, n: int = 12) -> list[tuple[int, int]]:
    y, m, out = today.year, today.month, []
    for _ in range(n):
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
        out.append((y, m))
    return out[::-1]


def split(total: int, days: list[int], rng: random.Random) -> list[int]:
    weights = [rng.uniform(0.6, 1.4) for _ in days]
    parts = [int(total * w / sum(weights)) for w in weights]
    parts[-1] += total - sum(parts)
    return parts


def transactions(c: dict, today: date) -> dict:
    """Операции по счёту: поступления в сумме дают ровно inflows, плюс регулярные платежи (их ищет K1)."""
    rng = random.Random(int(c["inn"]))
    months = months_back(today) + [(today.year, today.month)]
    outflows = c.get("outflows") or default_outflows(c)
    items = []
    for i, (y, m) in enumerate(months):
        last_day = calendar.monthrange(y, m)[1] if i < 12 else today.day - 1
        total = c["inflows"][i] if i < 12 else int(sum(c["inflows"][-3:]) / 3 * last_day / 30 * 0.85)
        if c.get("retail"):
            days = list(range(1, last_day + 1))
            purpose, counterparty = "Возмещение по операциям эквайринга", None
        else:
            days = sorted(rng.sample(range(1, last_day + 1), min(last_day, rng.randint(5, 8))))
            purpose, counterparty = "Оплата по договору поставки", "7700000000"
        for day, amount in zip(days, split(total, days, rng), strict=True):
            items.append({"bookingDate": f"{y}-{m:02d}-{day:02d}", "amount": f"{amount:.2f}", "direction": "in",
                          "counterpartyInn": counterparty, "purpose": purpose,
                          "category": "acquiring" if c.get("retail") else "customer_payment"})
        for purpose_out, day, amount, category in outflows:
            if day <= last_day:
                items.append({"bookingDate": f"{y}-{m:02d}-{day:02d}", "amount": f"{amount:.2f}", "direction": "out",
                              "counterpartyInn": None, "purpose": purpose_out, "category": category})
    items.sort(key=lambda t: (t["bookingDate"], t["direction"]))
    return {"accountInn": c["inn"], "account": "40702810" + c["inn"][-10:].rjust(12, "0"), "currency": "RUB",
            "balance": {"amount": f"{c['balance']:.2f}", "asOf": today.isoformat()}, "items": items}


# ── стабы ────────────────────────────────────────────────────────────────────────────────────────────────────────


def get_stub(name: str, pattern: str, keys: list[str], body: str, catch_all: str) -> dict:
    alt = "|".join(keys) or "-"
    return {"mappings": [
        {"name": name, "priority": 5, "request": {"method": "GET", "urlPathPattern": pattern.format(keys=f"({alt})")},
         "response": {"status": 200, "headers": JSON_HEADERS, "bodyFileName": body}},
        {"name": f"{name}: не найдено", "priority": 9, "request": {"method": "GET", "urlPathPattern": catch_all},
         "response": NOT_FOUND}]}


def query_stub(name: str, path: str, param: str, keys: list[str], body: str, empty: dict) -> dict:
    alt = "|".join(keys) or "-"
    return {"mappings": [
        {"name": name, "priority": 5,
         "request": {"method": "GET", "urlPath": path, "queryParameters": {param: {"matches": f"^({alt})$"}}},
         "response": {"status": 200, "headers": JSON_HEADERS, "bodyFileName": body}},
        {"name": f"{name}: пусто", "priority": 9, "request": {"method": "GET", "urlPath": path},
         "response": {"status": 200, "headers": JSON_HEADERS, "jsonBody": empty}}]}


def post_stub(name: str, path: str, keys: list[str], body: str) -> dict:
    alt = "|".join(keys) or "-"
    return {"mappings": [
        {"name": name, "priority": 5, "request": {"method": "POST", "urlPath": path, "bodyPatterns": [
            {"matchesJsonPath": {"expression": "$.subject.inn", "matches": f"^({alt})$"}}]},
         "response": {"status": 200, "headers": JSON_HEADERS, "bodyFileName": body}},
        {"name": f"{name}: не найдено", "priority": 9, "request": {"method": "POST", "urlPath": path},
         "response": NOT_FOUND}]}


def mappings(ul: list[str], ip: list[str], everyone: list[str], persons: list[str], suppliers: list[str]) -> None:
    seg = "{{request.pathSegments.[3]}}"
    write("mappings/egrul.json", get_stub("ЕГРЮЛ", "/egrul/v1/legal-entities/{keys}", ul,
                                          f"egrul/{seg}.json", "/egrul/v1/legal-entities/[^/]+"))
    write("mappings/egrip.json", get_stub("ЕГРИП", "/egrip/v1/entrepreneurs/{keys}", ip,
                                          f"egrip/{seg}.json", "/egrip/v1/entrepreneurs/[^/]+"))
    for ds in ("rsmp", "sshr", "paytax", "debtam", "snr"):
        write(f"mappings/fns-{ds}.json", get_stub(f"ФНС {ds}", f"/fns/v1/{ds}/{{keys}}", everyone,
                                                  f"fns/{ds}/{seg}.json", f"/fns/v1/{ds}/[^/]+"))
    write("mappings/fns-disqualified.json", {"mappings": [
        {"name": "ФНС: дисквалифицированные", "priority": 5, "request": {"method": "GET", "urlPath": "/fns/v1/disqualified"},
         "response": {"status": 200, "headers": JSON_HEADERS, "jsonBody": {"items": []}}}]})
    write("mappings/girbo.json", {"mappings": [
        *query_stub("ГИР БО: поиск", "/girbo/v1/organizations/search", "query", ul,
                    "girbo/search/{{request.query.query}}.json", {"content": []})["mappings"],
        *get_stub("ГИР БО: отчётность", "/girbo/v1/organizations/{keys}/bfo", ul, f"girbo/bfo/{seg}.json",
                  "/girbo/v1/organizations/[^/]+/bfo")["mappings"]]})
    write("mappings/legal-checks.json", get_stub("Юр. проверки", "/legal-checks/v1/{keys}", everyone,
                                                 "legal/{{request.pathSegments.[2]}}.json", "/legal-checks/v1/[^/]+"))
    for part, title in (("access", "доступы ДБО"), ("charter", "устав")):
        keys = everyone if part == "access" else ul
        write(f"mappings/bank-{part}.json", get_stub(f"Банк: {title}", f"/bank-core/v1/companies/{{keys}}/{part}", keys,
                                                     f"bank/{part}/{seg}.json", f"/bank-core/v1/companies/[^/]+/{part}"))
    write("mappings/bank-transactions.json", get_stub("Банк: операции", "/bank-core/v1/accounts/{keys}/transactions",
                                                      everyone, f"bank/tx/{seg}.json",
                                                      "/bank-core/v1/accounts/[^/]+/transactions"))
    write("mappings/bank-persons.json", get_stub("Банк: персоны", "/bank-core/v1/persons/{keys}", persons,
                                                 f"bank/persons/{seg}.json", "/bank-core/v1/persons/[^/]+"))
    write("mappings/bki.json", post_stub("БКИ: кредитный отчёт", "/bki/v1/credit-reports", everyone,
                                         "bki/{{jsonPath request.body '$.subject.inn'}}.json"))
    write("mappings/bki-info.json", post_stub("БКИ: информационная часть", "/bki/v1/info-part", everyone,
                                              "bki-info/{{jsonPath request.body '$.subject.inn'}}.json"))
    write("mappings/eis.json", query_stub("ЕИС: контракты", "/eis/v1/contracts", "supplierInn", suppliers,
                                          "eis/{{request.query.supplierInn}}.json", {"contracts": []}))
    write("mappings/mchd.json", {"mappings": [
        {"name": "МЧД: поиск", "priority": 5, "request": {"method": "GET", "urlPath": "/mchd/v1/poa"},
         "response": {"status": 200, "headers": JSON_HEADERS, "jsonBody": {"items": []}}},
        {"name": "МЧД: не найдена", "priority": 9, "request": {"method": "GET", "urlPathPattern": "/mchd/v1/poa/[^/]+"},
         "response": NOT_FOUND}]})
    write("mappings/abs.json", {"mappings": [   # выдача: ключ идемпотентности = id заявки (docs/07 §7, N7 — сценарий песочницы)
        {"name": "АБС: открыть счёт кредита", "priority": 5, "request": {"method": "POST", "urlPath": "/abs/v1/loans"},
         "response": {"status": 201, "headers": JSON_HEADERS, "jsonBody": {
             "loanId": "{{jsonPath request.body '$.applicationId'}}", "status": "OPENED"}}},
        {"name": "АБС: выдать", "priority": 5,
         "request": {"method": "POST", "urlPathPattern": "/abs/v1/loans/[^/]+/disburse"},
         "response": {"status": 200, "headers": JSON_HEADERS, "jsonBody": {
             "loanId": "{{request.pathSegments.[3]}}", "status": "DISBURSED", "disbursedAt": "{{now}}"}}},
        {"name": "АБС: статус", "priority": 5, "request": {"method": "GET", "urlPathPattern": "/abs/v1/loans/[^/]+"},
         "response": {"status": 200, "headers": JSON_HEADERS, "jsonBody": {
             "loanId": "{{request.pathSegments.[3]}}", "status": "OPENED"}}}]})


def main() -> None:
    world = yaml.safe_load(WORLD.read_text("utf-8"))
    today, people = date.fromisoformat(world["today"]), world["people"]
    for sub in ("__files", "mappings"):
        shutil.rmtree(OUT / sub, ignore_errors=True)

    ul, ip, suppliers = [], [], []
    for c in world["companies"]:
        inn = c["inn"]
        if is_ul(c):
            ul.append(inn)
            write(f"__files/egrul/{inn}.json", egrul(c, people))
            write(f"__files/girbo/search/{inn}.json",
                  {"content": [{"id": inn, "inn": inn, "ogrn": c["ogrn"], "shortName": c["name"]}]})
            write(f"__files/girbo/bfo/{inn}.json", girbo(c))
            write(f"__files/bank/charter/{inn}.json",
                  {"companyInn": inn, "decisionMethod": c["charter"]["decisionMethod"], "limits": []})
        else:
            ip.append(inn)
            write(f"__files/egrip/{inn}.json", egrip(c, people))
        for ds, body in fns(c, people).items():
            write(f"__files/fns/{ds}/{inn}.json", body)
        write(f"__files/legal/{inn}.json", {"inn": inn, "bankruptcy": {"stage": None, "efrsbDate": None},
                                            "arbitration": {"asDefendantCount": 0, "claimsSum": "0.00"},
                                            "enforcement": {"count": 0, "sum": "0.00"}, "sanctionsListHit": False})
        director = c.get("kyc_director") or (c["eio"][0][0] if is_ul(c) else c["owner"])
        write(f"__files/bank/access/{inn}.json", {"companyInn": inn, "kycDirectorInn": people[director]["inn"], "persons": [
            {"personInn": people[p]["inn"], "fio": " ".join(people[p]["fio"]), "level": level} for p, level in c["access"]]})
        write(f"__files/bank/tx/{inn}.json", transactions(c, today))
        write(f"__files/bki/{inn}.json", bki(c, today))
        write(f"__files/bki-info/{inn}.json", {"subject": {"inn": inn}, "requests": {"last30days": c["bki"]["requests"]},
                                               "refusals": {"last30days": 0}})
        if c.get("eis"):
            suppliers.append(inn)
            write(f"__files/eis/{inn}.json", {"contracts": [{**k, "price": f"{k['price']:.2f}", "treasurySupport": False}
                                                            for k in c["eis"]]})
    for key, person in people.items():
        write(f"__files/bank/persons/{person['inn']}.json",
              {"personInn": person["inn"], "fio": " ".join(person["fio"]), "kycStatus": "VERIFIED", "key": key})
    mappings(ul, ip, ul + ip, [p["inn"] for p in people.values()], suppliers)
    print(f"wiremock: {len(world['companies'])} компаний, {len(people)} человек → {OUT}")


if __name__ == "__main__":
    main()
