"""Коллекция запросов Postman: uv run python -m qa.postman → docs/api/postman_collection.json

Собрана из того же, что проверяют тесты: сценарии ролей — из seed/flows.py (их прокликивает tests/e2e/test_flows.py),
тела запросов — как в e2e. Запуск — Collection Runner в Postman или `newman run` по поднятому стенду: шаги конвейера
ждут нужный статус опросом заявки (до 30 с). Руками файл не правят; детерминирован.
"""

import json
import uuid
from pathlib import Path

from seed import world
from seed.flows import ACTION_TEXT, ARG_TEXT, FLOWS

OUT = Path(__file__).resolve().parents[2] / "docs" / "api" / "postman_collection.json"
NS = uuid.UUID("6f1d3c2a-9b7e-4c55-8a10-2f6e5d4c3b2a")
COMPANIES = {c["key"]: c for c in world.load()["companies"]}
SMIRNOVA = COMPANIES["smirnova"]["inn"]
DOCUMENTS = {"documents": ["Пояснения к отчётности.pdf"], "comment": "Пояснения по запросу специалиста"}


def _js(*lines: str) -> list[str]:
    return list(lines)


def _expect(code: int) -> list[str]:
    return _js(f'pm.test("HTTP {code}", () => pm.response.to.have.status({code}));')


def _status(want: str) -> list[str]:
    return _js(f'pm.test("статус {want}", () => pm.expect(pm.response.json().data.status).to.eql("{want}"));')


def _save(var: str, path: str) -> list[str]:
    return _js(f'pm.collectionVariables.set("{var}", pm.response.json().data.{path});')


def _wait(want: str) -> list[str]:
    """Опрос заявки, пока worker не доведёт её до нужного статуса: тот же запрос ещё раз через секунду, до 30 раз."""
    return _js(
        "const got = pm.response.json().data.status;",
        'const tries = Number(pm.collectionVariables.get("tries") || 0);',
        f'if (got !== "{want}" && tries < 30) {{',
        '    pm.collectionVariables.set("tries", tries + 1);',
        "    setTimeout(() => {}, 1000);",
        "    pm.execution.setNextRequest(pm.info.requestName);",
        "} else {",
        '    pm.collectionVariables.set("tries", 0);',
        f'    pm.test("статус {want}", () => pm.expect(got).to.eql("{want}"));',
        "}",
    )


def _pause(ms: int) -> list[str]:
    return _js(f"setTimeout(() => {{}}, {ms});      // worker обновляет данные компании")


def _item(name: str, method: str, path: str, *, user: str | None = None, body=None, tests: list[str] = (),
          headers: dict | None = None, description: str = "") -> dict:
    hdr = [{"key": "Authorization", "value": f"Bearer {{{{token_{user}}}}}"}] if user else []
    hdr += [{"key": k, "value": v} for k, v in (headers or {}).items()]
    path, _, query = path.partition("?")
    url = {"raw": "{{base}}" + path + (f"?{query}" if query else ""), "host": ["{{base}}"],
           "path": [p for p in path.split("/") if p]}
    if query:
        url["query"] = [{"key": k, "value": v} for k, v in (q.split("=") for q in query.split("&"))]
    request = {"method": method, "header": hdr, "url": url}
    if body is not None:
        hdr.append({"key": "Content-Type", "value": "application/json"})
        request["body"] = {"mode": "raw", "raw": json.dumps(body, ensure_ascii=False, indent=2)}
    if description:
        request["description"] = description
    item = {"name": name, "request": request}
    if tests:
        item["event"] = [{"listen": "test", "script": {"type": "text/javascript", "exec": list(tests)}}]
    return item


def _folder(name: str, items: list[dict], description: str = "") -> dict:
    return {"name": name, "description": description, "item": items}


def _login(user: str, n: str) -> dict:
    return _item(f"{n} войти: {user}", "POST", f"/sandbox/personas/{user}/login?wait_s=10",
                 tests=[*_expect(200), *_save(f"token_{user}", "token")])


def _simulator() -> dict:
    flagged = {"full_name": "Олег Петров", "organization": "ООО «Пекарня у дома»", "okved": "10.71", "flags": ["tax_debt"]}
    return _folder("0. Вход и мир симулятора", [
        _item("0.0 продукты для главной страницы", "GET", "/catalog/products?lang=ru", tests=_expect(200)),
        _item("0.1 сбросить мир", "POST", "/sandbox/reset", tests=_expect(200)),
        _item("0.2 кто есть: пользователи", "GET", "/sandbox/personas?lang=ru", tests=_expect(200)),
        _item("0.3 войти по ID: s7", "POST", "/auth/login?wait_s=10", body={"login": "s7"},
              tests=[*_expect(200), *_save("token_s7", "token")]),
        _item("0.4 мои компании и права", "GET", "/me", user="s7", tests=_expect(200)),
        _item("0.5 своя компания: параметры и флаги", "GET", "/sandbox/persona-options?lang=ru", tests=_expect(200)),
        _item("0.5a гид: сценарии по ролям", "GET", "/sandbox/scenarios?lang=ru", tests=_expect(200)),
        _item("0.6 своя компания с недоимкой", "POST", "/sandbox/personas", body=flagged, tests=[*_expect(201), _js(
            'pm.test("сценарий из флага", () => pm.expect(pm.response.json().data.scenario).to.include("недоимка"));')[0]]),
    ], "Вход по ID → токен в переменную token_<id>. Перелогин — тот же вход другим пользователем.")


def _officer() -> dict:
    bank = world.load()["bank"]["inn"]
    return _folder("1a. Рабочее место специалиста", [
        _item("1a.1 войти по ID: bank", "POST", "/auth/login?wait_s=0", body={"login": "bank"},
              tests=[*_expect(200), *_save("token_bank", "token")]),
        _item("1a.2 карточки: очередь, второй ключ, выдачи", "GET", f"/demo-personas/{bank}/dashboard/summary", user="bank",
              tests=_expect(200)),
        _item("1a.3 очередь заявок", "GET", "/bank/queue", user="bank", tests=_expect(200)),
        _item("1a.4 метрики конвейера: STP и время решения", "GET", "/bank/metrics", user="bank", tests=_expect(200)),
        _item("1a.5 журнал аудита: цепочка хэшей цела", "GET", "/bank/audit", user="bank", tests=[*_expect(200), _js(
            'pm.test("цепочка цела", () => pm.expect(pm.response.json().data.intact).to.eql(true));')[0]]),
    ], "ИНН банка открывает рабочее место сотрудника — тот же кабинет, что у клиента, но с очередью.")


def _cabinet() -> dict:
    c = f"/companies/{SMIRNOVA}"
    return _folder("1. Кабинет компании (S7, ИП Смирнова)", [
        _item("1.1 кто работает в кабинете", "GET", f"/demo-personas/{SMIRNOVA}", user="s7", tests=_expect(200)),
        _item("1.2 карточки главной", "GET", f"/demo-personas/{SMIRNOVA}/dashboard/summary", user="s7", tests=_expect(200)),
        _item("1.3 K1 прогноз остатка и K2 предложение", "GET", f"{c}/insights", user="s7", tests=[
            *_expect(200), 'pm.test("разрыв 28.10", () => pm.expect(pm.response.json().data.cash_forecast.cash_gap.date)'
                           '.to.eql("2026-10-28"));']),
        _item("1.4 предодобренные продукты", "GET", f"{c}/products", user="s7", tests=_expect(200)),
        _item("1.5 кредитное здоровье: балл и рычаги", "GET", f"{c}/score", user="s7", tests=_expect(200)),
        _item("1.5a как гасить: график или доля поступлений", "GET", f"{c}/repayment?amount=400000&term_months=12", user="s7",
              tests=_expect(200)),
        _item("1.6 что банк знает о компании", "GET", f"{c}/profile", user="s7", tests=_expect(200)),
        _item("1.7 заявки и задачи на главной", "GET", f"{c}/applications/summary", user="s7", tests=_expect(200)),
        _item("1.8 входящие пользователя", "GET", "/tasks", user="s7", tests=_expect(200)),
    ])


def _main_path() -> dict:
    a = "/applications/{{app_id}}"
    return _folder("2. Заявка от подачи до выдачи (S7, овердрафт)", [
        _item("2.1 создать заявку", "POST", "/applications", user="s7", tests=[*_expect(201), *_save("app_id", "id")],
              body={"inn": SMIRNOVA, "product": "OVERDRAFT", "amount": 400000, "goal": "cash_gap", "consent_bki": True}),
        _item("2.2 подать", "POST", f"{a}/submit", user="s7", headers={"Idempotency-Key": "{{app_id}}"},
              tests=[*_expect(200), *_status("SUBMITTED")]),
        _item("2.3 ждём решение → OFFERED", "GET", a, user="s7", tests=_wait("OFFERED")),
        _item("2.4 почему так", "GET", f"{a}/explain", user="s7", tests=_expect(200)),
        _item("2.5 принять оферту", "POST", f"{a}/offer/accept", user="s7", body={"variant": 0},
              tests=[*_expect(200), *_status("SIGNING")]),
        _item("2.6 подписать", "POST", f"{a}/signatures", user="s7", tests=[*_expect(200), *_status("SIGNED")]),
        _item("2.7 ждём выдачу → ISSUED", "GET", a, user="s7", tests=_wait("ISSUED")),
        _item("2.8 история заявки", "GET", f"{a}/events", user="s7", tests=_expect(200)),
    ])


def _step(flow, step, n: str, company: dict, request: dict) -> dict | list[dict]:
    a = "/applications/{{app_id}}"
    action = ACTION_TEXT[step.action] + (f" {ARG_TEXT.get(step.arg, step.arg)}" if step.arg is not None else "")
    name = f"{n} {step.user if step.user != 'system' else 'конвейер'}: {action}" + (f" → {step.status}" if step.status else "")
    sync = _status(step.status) if step.status else []
    u = None if step.user == "system" else step.user
    match step.action:
        case "create":
            return _item(name, "POST", "/applications", user=u, tests=[*_expect(201), *_save("app_id", "id"), *sync],
                         body={"inn": company["inn"], **request, "consent_bki": True})
        case "submit" | "withdraw":
            return _item(name, "POST", f"{a}/{step.action}", user=u, tests=[*_expect(200), *sync])
        case "run":
            return _item(name, "GET", a, user=flow_client(flow), tests=_wait(step.status))
        case "vote":
            return _item(name, "POST", f"{a}/approvals/vote", user=u, body={"vote": step.arg}, tests=[*_expect(200), *sync])
        case "accept":
            return _item(name, "POST", f"{a}/offer/accept", user=u, body={"variant": 0}, tests=[*_expect(200), *sync])
        case "decline":
            return _item(name, "POST", f"{a}/offer/decline", user=u, tests=[*_expect(200), *sync])
        case "sign":
            return _item(name, "POST", f"{a}/signatures", user=u, tests=[*_expect(200), *sync])
        case "answer":
            body = DOCUMENTS if step.arg == "documents" else {"corporate_approval": True}
            return _item(name, "POST", f"{a}/info-requests/answer", user=u, body=body, tests=[*_expect(200), *sync])
        case "bank":
            body = {"action": step.arg, "comment": "решение специалиста"}
            if step.arg == "request_info":
                body["asks"] = ["REQ_DOCUMENTS"]
            return _item(name, "POST", f"/bank{a}/decision", user=u, body=body, tests=[*_expect(200), *sync])
        case "confirm":
            return _item(name, "POST", f"/bank{a}/decision/confirm", user=u, body={"approve": step.arg},
                         tests=[*_expect(200), *sync])
        case "event":
            return [_item(name.split(" → ")[0], "POST", "/sandbox/events", body={"type": step.arg, "inn": company["inn"]},
                          tests=[*_expect(202), *_pause(3000)]),
                    _item(f"{n}a ждём статус {step.status}", "GET", a, user=flow_client(flow), tests=_wait(step.status))]
        case "forbidden":
            calls = {"create": ("POST", "/applications", {"inn": company["inn"], **request}),
                     "sign": ("POST", f"{a}/signatures", None),
                     "confirm": ("POST", f"/bank{a}/decision/confirm", {"approve": True})}
            method, path, body = calls[step.arg]
            return _item(name, method, path, user=u, body=body, tests=_expect(403), description=step.note)
    raise ValueError(step.action)


def flow_client(flow) -> str:
    """От чьего имени опрашивать заявку в шагах конвейера: первый клиент сценария, который её видит."""
    return next(s.user for s in flow.steps if s.action == "create")


def _flows() -> list[dict]:
    out = []
    for i, flow in enumerate(FLOWS, 3):
        company = COMPANIES[flow.company]
        request = flow.request or company["scenario"]["request"]
        users = list(dict.fromkeys(s.user for s in flow.steps if s.user != "system"))
        items = [_login(user, f"{i}.0.{k}") for k, user in enumerate(users, 1)]
        for n, step in enumerate(flow.steps, 1):
            made = _step(flow, step, f"{i}.{n}", company, request)
            items += made if isinstance(made, list) else [made]
        out.append(_folder(f"{i}. {flow.title}", items, flow.about))
    return out


ABOUT = ("Сгенерировано: `cd backend && uv run python -m qa.postman`. Стенд — `cd infra && docker compose up --build`, "
         "`base` = http://localhost:8080/api/v1 (через nginx фронта) или http://localhost:8000/api/v1 (напрямую). "
         "Запускать папки по порядку в Collection Runner или `newman run`: шаги конвейера ждут статус опросом. "
         "Сценарии ролей — те же, что в docs/15_roles.md §4 и tests/e2e/test_flows.py.")


def collection() -> dict:
    return {
        "info": {"_postman_id": str(uuid.uuid5(NS, "alfa-horizon")), "name": "Alfa Horizon — кредитный кабинет",
                 "description": ABOUT, "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
        "variable": [{"key": "base", "value": "http://localhost:8080/api/v1"}, {"key": "app_id", "value": ""},
                     {"key": "tries", "value": "0"}],
        "item": [_simulator(), _cabinet(), _officer(), _main_path(), *_flows()],
    }


def main() -> None:
    OUT.write_text(json.dumps(collection(), ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
