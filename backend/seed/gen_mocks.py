"""Генератор моков WireMock из мира симулятора: uv run python -m seed.gen_mocks

seed/personas.yaml → seed/world.py (проверка + ответы источников) → wiremock/__files/<источник>/<ключ>.json
и wiremock/mappings/*.json (по файлу стабов на ручку: тело выбирается по ИНН шаблоном, незнакомый ИНН → 404).
Руками JSON не пишем (docs/06 §12). Детерминированно: тот же personas.yaml → те же файлы (тест и CI сверяют).
"""

import json
import shutil
import sys
from datetime import date
from pathlib import Path

from seed import world

OUT = Path(__file__).resolve().parents[1] / "wiremock"
JSON_HEADERS = {"Content-Type": "application/json; charset=utf-8"}
NOT_FOUND = {"status": 404, "headers": {"Content-Type": "application/problem+json"},
             "jsonBody": {"type": "about:blank", "title": "Not Found", "status": 404, "detail": "Запись не найдена"}}


def write(out: Path, rel: str, obj) -> None:
    path = out / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n", "utf-8")


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


def mappings(out: Path, ul: list[str], ip: list[str], msp: list[str], persons: list[str], suppliers: list[str],
             principals: list[str]) -> None:
    everyone, seg = ul + ip, "{{request.pathSegments.[3]}}"
    stubs = {
        "egrul": get_stub("ЕГРЮЛ", "/egrul/v1/legal-entities/{keys}", ul, f"egrul/{seg}.json", "/egrul/v1/legal-entities/[^/]+"),
        "egrip": get_stub("ЕГРИП", "/egrip/v1/entrepreneurs/{keys}", ip, f"egrip/{seg}.json", "/egrip/v1/entrepreneurs/[^/]+"),
        "fns-disqualified": {"mappings": [
            {"name": "ФНС: дисквалифицированные", "priority": 5,
             "request": {"method": "GET", "urlPath": "/fns/v1/disqualified"},
             "response": {"status": 200, "headers": JSON_HEADERS, "jsonBody": {"items": []}}}]},
        "girbo": {"mappings": [
            *query_stub("ГИР БО: поиск", "/girbo/v1/organizations/search", "query", ul,
                        "girbo/search/{{request.query.query}}.json", {"content": []})["mappings"],
            *get_stub("ГИР БО: отчётность", "/girbo/v1/organizations/{keys}/bfo", ul, f"girbo/bfo/{seg}.json",
                      "/girbo/v1/organizations/[^/]+/bfo")["mappings"]]},
        "legal-checks": get_stub("Юр. проверки", "/legal-checks/v1/{keys}", everyone,
                                 "legal/{{request.pathSegments.[2]}}.json", "/legal-checks/v1/[^/]+"),
        "bank-transactions": get_stub("Банк: операции", "/bank-core/v1/accounts/{keys}/transactions", everyone,
                                      f"bank/tx/{seg}.json", "/bank-core/v1/accounts/[^/]+/transactions"),
        "bank-persons": get_stub("Банк: персоны", "/bank-core/v1/persons/{keys}", persons, f"bank/persons/{seg}.json",
                                 "/bank-core/v1/persons/[^/]+"),
        "bki": post_stub("БКИ: кредитный отчёт", "/bki/v1/credit-reports", everyone,
                         "bki/{{jsonPath request.body '$.subject.inn'}}.json"),
        "bki-info": post_stub("БКИ: информационная часть", "/bki/v1/info-part", everyone,
                              "bki-info/{{jsonPath request.body '$.subject.inn'}}.json"),
        "eis": query_stub("ЕИС: контракты", "/eis/v1/contracts", "supplierInn", suppliers,
                          "eis/{{request.query.supplierInn}}.json", {"contracts": []}),
        "mchd": {"mappings": [
            *query_stub("МЧД: поиск по доверителю", "/mchd/v1/poa", "principalInn", principals,
                        "mchd/{{request.query.principalInn}}.json", {"items": []})["mappings"],
            {"name": "МЧД: не найдена", "priority": 9, "request": {"method": "GET", "urlPathPattern": "/mchd/v1/poa/[^/]+"},
             "response": NOT_FOUND}]},
        "abs": {"mappings": [   # выдача: ключ идемпотентности = id заявки (docs/07 §7)
            {"name": "АБС: открыть счёт кредита", "priority": 5, "request": {"method": "POST", "urlPath": "/abs/v1/loans"},
             "response": {"status": 201, "headers": JSON_HEADERS, "jsonBody": {
                 "loanId": "{{jsonPath request.body '$.applicationId'}}", "status": "OPENED"}}},
            {"name": "АБС: выдать", "priority": 5,
             "request": {"method": "POST", "urlPathPattern": "/abs/v1/loans/[^/]+/disburse"},
             "response": {"status": 200, "headers": JSON_HEADERS, "jsonBody": {
                 "loanId": "{{request.pathSegments.[3]}}", "status": "DISBURSED", "disbursedAt": "{{now}}"}}},
            {"name": "АБС: статус", "priority": 5, "request": {"method": "GET", "urlPathPattern": "/abs/v1/loans/[^/]+"},
             "response": {"status": 200, "headers": JSON_HEADERS, "jsonBody": {
                 "loanId": "{{request.pathSegments.[3]}}", "status": "OPENED"}}}]},
    }
    for ds in ("rsmp", "sshr", "paytax", "debtam", "snr"):
        stubs[f"fns-{ds}"] = get_stub(f"ФНС {ds}", f"/fns/v1/{ds}/{{keys}}", msp if ds == "rsmp" else everyone,
                                      f"fns/{ds}/{seg}.json", f"/fns/v1/{ds}/[^/]+")
    for part, title, keys in (("access", "доступы ДБО", everyone), ("charter", "устав", ul)):
        stubs[f"bank-{part}"] = get_stub(f"Банк: {title}", f"/bank-core/v1/companies/{{keys}}/{part}", keys,
                                         f"bank/{part}/{seg}.json", f"/bank-core/v1/companies/[^/]+/{part}")
    for name, body in stubs.items():
        write(out, f"mappings/{name}.json", body)


def main(out: Path = OUT) -> None:
    data = world.load()
    today, people = date.fromisoformat(data["today"]), data["people"]
    errors = {c["key"]: e for c in data["companies"] if (e := world.validate(c, people, today))}
    if errors:
        sys.exit("мир симулятора некорректен:\n" + "\n".join(f"  {k}: {'; '.join(v)}" for k, v in errors.items()))
    for sub in ("__files", "mappings"):
        shutil.rmtree(out / sub, ignore_errors=True)

    ul, ip, msp, suppliers, principals = [], [], [], [], []
    for c in data["companies"]:
        inn = c["inn"]
        (ul if world.is_ul(c) else ip).append(inn)
        bodies = world.payloads(c, people, today)
        for source, body in bodies.items():
            write(out, f"__files/{world.FILES[source]}/{inn}.json", body)
        if "rsmp" in bodies:
            msp.append(inn)
        if "eis" in bodies:
            suppliers.append(inn)
        if "mchd" in bodies:
            principals.append(inn)
        if world.is_ul(c):
            write(out, f"__files/girbo/search/{inn}.json", world.girbo_search(c))
    for key, person in people.items():
        write(out, f"__files/bank/persons/{person['inn']}.json", world.person_card(key, person, data["companies"]))
    mappings(out, ul, ip, msp, [p["inn"] for p in people.values()], suppliers, principals)
    print(f"wiremock: {len(data['companies'])} компаний, {len(people)} человек → {out}")


if __name__ == "__main__":
    main()
