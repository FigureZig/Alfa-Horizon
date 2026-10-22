"""Симулятор (docs/08): вход пользователем, своя компания, отказы источников и события мира на лету, часы,
пауза воркера, «что если». Только при DEMO_MODE: в бою эти ручки не регистрируются.

Всё меняет только данные моков WireMock (admin API) и kv — продукт сам замечает изменения, как в бою.
"""

import asyncio
import copy
import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field

from seed import flags, world
from seed.flows import ACTION_TEXT, ACTION_TEXT_EN, ARG_TEXT, ARG_TEXT_EN, EN, FLOWS

from .. import auth, clock, personas, store
from ..config import settings
from ..domain import engine
from ..policy import load as load_policy
from ..policy import sources as source_config
from . import schemas as S
from .client import my_companies
from .deps import actor_of
from .http import Problem, ok
from .schemas import doc

router = APIRouter(prefix="/sandbox", tags=["simulator"])
auth_router = APIRouter(prefix="/auth", tags=["auth"])
ADMIN = f"{settings.wiremock_url}/__admin"
JSON_HEADERS = {"Content-Type": "application/json; charset=utf-8"}
PERSONA_BASE = 9000                      # номера своих персон: ИНН 7705…/7706…/7707… не пересекаются с миром симулятора
OVERRIDES_KEY = "sandbox:world_overrides"
Lang = Annotated[Literal["ru", "en"], Query(description="язык текстов карточек")]
WaitS = Annotated[float, Query(ge=0, le=15, description="сколько ждать, пока банк соберёт данные компаний, с")]


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(trust_env=False, timeout=10)


async def _drop(created_by: str) -> None:
    async with _client() as client:
        resp = await client.post(f"{ADMIN}/mappings/find-by-metadata",
                                 json={"matchesJsonPath": {"expression": "$.createdBy", "equalTo": created_by}})
        resp.raise_for_status()
        for m in resp.json().get("mappings", []):
            await client.delete(f"{ADMIN}/mappings/{m['id']}")


async def _import(stubs: list[dict]) -> None:
    async with _client() as client:
        resp = await client.post(f"{ADMIN}/mappings/import", json={
            "mappings": stubs, "importOptions": {"duplicatePolicy": "OVERWRITE", "deleteAllNotInImport": False}})
        resp.raise_for_status()


@router.get("/presets", **doc(S.PresetsResponse, summary="Компании мира и их эталонные исходы"))
async def presets():
    """Компании мира симулятора и их эталонные сценарии (seed/personas.yaml → моки WireMock)."""
    data = world.load()
    return ok([{"key": c["key"], "inn": c["inn"], "name": c["name"], "okved": c["okved"], "scenario": c.get("scenario")}
               for c in data["companies"]], today=data["today"])


# ── стабы WireMock ───────────────────────────────────────────────────────────────────────────────────────────────


def match(src: dict, inn: str | None) -> dict:
    """Как WireMock узнаёт запрос worker к источнику (пути — policy/sources.yaml); inn=None — любой ИНН."""
    path, _, query = src["path"].partition("?")
    request: dict = {"method": src["method"]}
    if src["method"] == "POST":
        request["urlPath"] = path
        if inn:
            request["bodyPatterns"] = [{"matchesJsonPath": {"expression": "$.subject.inn", "equalTo": inn}}]
    elif query:                                             # ИНН в параметре запроса (ЕИС)
        request["urlPath"] = path
        request["queryParameters"] = {query.split("=")[0]: {"equalTo": inn} if inn else {"matches": ".*"}}
    elif inn:
        request["urlPath"] = path.replace("{inn}", inn)
    else:
        request["urlPathPattern"] = re.escape(path).replace(re.escape("{inn}"), "[0-9]+")
    return request


def persona_stubs(company: dict, people: dict, on: date, *, priority: int = 3, created_by: str = "sandbox-persona",
                  only: set[str] | None = None) -> list[dict]:
    """Ответы источников о компании: приоритет 3 — своя персона (выше штатных 5 и «не найдено» 9),
    2 — событие мира поверх неё, 1 — отказ источника поверх всего."""
    cfg, inn = source_config(), company["inn"]
    meta = {"createdBy": created_by, "inn": inn, "name": company["name"]}

    def stub(request: dict, body, source: str) -> dict:
        return {"priority": priority, "request": request,
                "response": {"status": 200, "headers": JSON_HEADERS, "jsonBody": body}, "metadata": {**meta, "source": source}}

    served = world.served(company, people, on)
    stubs = [stub(match(cfg["sources"][s], inn), body, s) for s, body in served.items() if only is None or s in only]
    if only is None:
        stubs += [stub({"method": "GET", "urlPath": f"/bank-core/v1/persons/{p['inn']}"}, world.person_card(key, p, [company]),
                       "bank_person") for key, p in people.items()]
        if world.is_ul(company):
            stubs.append(stub({"method": "GET", "urlPath": "/girbo/v1/organizations/search",
                               "queryParameters": {"query": {"equalTo": inn}}}, world.girbo_search(company), "girbo_search"))
    return stubs


# ── персоны «Кто я» ──────────────────────────────────────────────────────────────────────────────────────────────


@router.get("/personas", **doc(S.PersonaCardsResponse, summary="Пользователи для входа"))
async def list_personas(lang: Lang = "ru"):
    """Персоны для экрана входа: пресеты сценариев и свои. Карточка считается из мира (права, профиль, реестры)."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        items = await personas.all_personas(conn)
    return ok([personas.card(p, lang) for p in items])


class PersonaIn(BaseModel):
    """Своя персона. Поля карточки — как у фронта (SandboxPersonaCreateDto); незаданные тексты бэкенд посчитает сам.
    Параметры компании строят ИНН, ОГРН, людей, выписку, КИ и отчётность тем же seed/world.py, что и мир симулятора."""
    model_config = ConfigDict(json_schema_extra={"examples": [
        {"full_name": "Олег Петров", "organization": "ООО «Пекарня у дома»", "okved": "10.71", "okved_name": "Производство хлеба",
         "inflow_avg": 2400000, "flags": ["tax_debt"]}]})
    kind: Literal["client", "bank"] = "client"
    full_name: str | None = Field(None, max_length=120, description="«Имя Фамилия» или «Фамилия Имя Отчество»")
    inn: str | None = Field(None, description="ИНН компании: 10 цифр — ООО или АО, 12 — ИП; пусто — сгенерируем")
    organization: str | None = Field(None, max_length=200, description="название компании (клиент) или роль (банк)")
    code: str | None = Field(None, max_length=20)
    scenario: str | None = Field(None, max_length=200)
    permissions: str | None = Field(None, max_length=300)
    profile: str | None = Field(None, max_length=300)
    registries: str | None = Field(None, max_length=300)
    preview: str | None = Field(None, max_length=300)
    login_label: str | None = Field(None, max_length=60)
    form: Literal["IP", "LLC", "JSC"] = Field("LLC", description="ИП, ООО или АО; если задан ИНН — по его длине")
    okved: str = Field("62.01", pattern=r"^\d{2}(\.\d{1,2}){0,2}$", description="ОКВЭД 2: от него отрасль, продукты, спред")
    okved_name: str = Field("Основной вид деятельности", max_length=300, description="название вида деятельности")
    age_months: int = Field(36, ge=1, le=600, description="сколько месяцев бизнесу")
    headcount: int = Field(12, ge=1, le=250, description="сотрудников — от численности категория МСП")
    inflow_avg: int = Field(3_000_000, ge=10_000, description="средние поступления на счёт в месяц, ₽")
    inflow_cv: float = Field(0.3, ge=0, le=1, description="разброс поступлений от месяца к месяцу")
    inflow_trend: float = Field(0.0, ge=-0.9, le=1, description="последние 3 месяца к предыдущим 9, минус 1")
    debt_load: float = Field(0.15, ge=0, le=1, description="платежи по текущим кредитам / поступления")
    overdue_days: int = Field(0, ge=0, le=365, description="максимальная просрочка в КИ")
    bki_requests: int = Field(1, ge=0, le=50, description="запросы в БКИ за 30 дней")
    tax_debt: int = Field(0, ge=0, description="недоимка, ₽")
    participants: int = Field(1, ge=1, le=10, description="участников ООО")
    profit_margin: float = Field(0.05, ge=-1, le=1, description="чистая прибыль / выручка")
    contract_price: int | None = Field(None, gt=0, description="действующий госконтракт в ЕИС, ₽")
    flags: list[str] = Field([], description="флаги из каталога GET /sandbox/persona-options: недоимка, банкротство, "
                             "просрочка, крупная сделка, БКИ не отвечает… Задают параметры поверх полей и обязаны менять решение",
                             examples=[["tax_debt", "bki_down"]])


TEXT_FIELDS = ("organization", "scenario", "permissions", "profile", "registries", "preview", "login_label")
PARAMS = ("form", "okved", "okved_name", "age_months", "headcount", "inflow_avg", "inflow_cv", "inflow_trend", "debt_load",
          "overdue_days", "bki_requests", "tax_debt", "participants", "profit_margin", "contract_price")
FORMS = {"IP": {"ru": "ИП", "en": "Sole proprietor"}, "LLC": {"ru": "ООО", "en": "LLC"}, "JSC": {"ru": "АО", "en": "JSC"}}


def _param(name: str) -> dict:
    field = PersonaIn.model_fields[name]
    bounds = {type(m).__name__.lower(): getattr(m, type(m).__name__.lower()) for m in field.metadata
              if type(m).__name__ in ("Ge", "Le", "Gt")}
    kind = {int: "integer", float: "number", str: "string"}.get(field.annotation, "string")
    if name == "form":
        kind = "enum"
    return {"id": name, "type": kind, "default": field.default, "description": field.description, **bounds}


@router.get("/persona-options", **doc(S.PersonaOptionsResponse, summary="Своя компания: параметры и флаги"))
async def persona_options(lang: Lang = "ru"):
    """Что можно задать своей компании: форма, параметры с границами и флаги, которые реально меняют решение."""
    cat = flags.catalog()
    return ok({"forms": [{"id": k, "title": v[lang]} for k, v in FORMS.items()],
               "groups": [{"id": k, "title": v[lang]} for k, v in cat["groups"].items()],
               "flags": [{"id": k, "group": f["group"], "title": f["title"][lang], "effect": f["effect"][lang],
                          "forms": f["forms"]} for k, f in cat["flags"].items()],
               "params": [_param(name) for name in PARAMS]})


async def _check_inn(conn, inn: str | None) -> str | None:
    """Свой ИНН — с верной контрольной цифрой и не занятый компаниями симулятора."""
    inn = (inn or "").strip() or None
    if inn is None:
        return None
    if not world.inn_valid(inn):
        fixed = world.inn_ul(inn[:9]) if len(inn) == 10 else world.inn_fl(inn[:10]) if len(inn) == 12 else None
        raise Problem(422, "INN_INVALID", "ИНН с неверной контрольной цифрой" + (f" — например, {fixed}" if fixed else ""),
                      inn=inn, suggested_inn=fixed)
    taken = {c["inn"] for p in await personas.all_personas(conn) for c in p.get("companies", [])} | {personas.bank()["inn"]}
    if inn in taken:
        raise Problem(409, "INN_TAKEN", "компания с таким ИНН уже есть в симуляторе", inn=inn)
    return inn


def parse_fio(full_name: str | None) -> list[str] | None:
    parts = (full_name or "").split()
    if len(parts) >= 3:
        return parts[:3]                     # Фамилия Имя Отчество
    if len(parts) == 2:
        return [parts[1], parts[0], ""]      # «Имя Фамилия» — как в подсказке фронта
    return None


def company_title(organization: str | None) -> str | None:
    """«ООО «Ромашка»», «Ромашка» → «Ромашка» — ОПФ ставит генератор по форме."""
    text = (organization or "").strip()
    if "«" in text:
        text = text.split("«", 1)[1].split("»", 1)[0]
    text = re.sub(r"^(ООО|АО|ПАО|ЗАО|ОАО)\s+", "", text).strip(" «»\"")
    return text or None


@router.post("/personas", status_code=201,
             **doc(S.PersonaCardResponse, 409, 422, status=201, summary="Создать свою компанию и её пользователя"))
async def create_persona(body: PersonaIn, lang: Lang = "ru"):
    """Собрать свою персону: компания встаёт в WireMock на лету (приоритет 3), worker сразу подтягивает её данные."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        inn = await _check_inn(conn, body.inn) if body.kind == "client" else None
        seq = await store.kv_get(conn, "users:custom_seq", 0) + 1
        await store.kv_set(conn, "users:custom_seq", seq)
        today = await clock.today(conn)
    form = ("IP" if len(inn) == 12 else ("JSC" if body.form == "JSC" else "LLC")) if inn else body.form
    if body.kind == "client" and (bad := flags.unknown(body.flags)):
        raise Problem(422, "FLAG_UNKNOWN", f"нет таких флагов: {', '.join(bad)}", flags=bad,
                      known=sorted(flags.catalog()["flags"]))
    if body.kind == "client" and (bad := flags.not_applicable(form, body.flags)):
        raise Problem(422, "FLAG_NOT_APPLICABLE", f"для формы {form} не бывает: {', '.join(bad)}", flags=bad, form=form)
    number = PERSONA_BASE + seq % 1000
    texts = {k: getattr(body, k) for k in TEXT_FIELDS if getattr(body, k)}
    titles = [flags.catalog()["flags"][f]["title"] for f in body.flags] if body.kind == "client" else []
    base = {"code": body.code or f"C{seq}", "faults": [], "texts": texts, "custom": True,
            "title": {"ru": body.scenario or ("Своя компания: " + ", ".join(t["ru"].lower() for t in titles) if titles
                                              else "Своя персона"),
                      "en": body.scenario or ("Your company: " + ", ".join(t["en"].lower() for t in titles) if titles
                                              else "Custom persona")},
            "preview": {"ru": body.preview or "Своя компания: подбор, заявка, решение и подпись",
                        "en": body.preview or "Your own company: matching, application, decision and signing"}}
    if body.kind == "bank":
        fio = parse_fio(body.full_name) or ["Соколова", "Мария", "Андреевна"]
        role = body.organization or "Кредитный специалист"
        persona = {**base, "id": f"b{seq}", "kind": "bank", "staff": {"key": f"staff{seq}", "fio": fio,
                                                                       "role": {"ru": role, "en": role}}}
        created_personas = [persona]
    else:
        card_fields = {"kind", "form", "okved", "okved_name", "full_name", "organization", "code", "inn", "flags", *TEXT_FIELDS}
        spec = {**body.model_dump(exclude=card_fields), "inn": inn,
                "kind": form, "okved": [body.okved, body.okved_name], "owner_fio": parse_fio(body.full_name),
                "company_name": company_title(body.organization) if form != "IP" else None}
        spec, base["faults"] = flags.apply(spec, body.flags)
        company, people = world.custom(spec, number, today)
        errors = world.validate(company, people, today)
        if errors:
            raise Problem(422, "PERSONA_INVALID", "такой компании не бывает: " + "; ".join(errors), errors=errors)
        await _import(persona_stubs(company, people, today))
        owner = company.get("owner") or company["eio"][0][0]
        persona = {**base, "id": f"c{seq}", "kind": "client", "person": {"key": owner, **people[owner]},
                   "companies": [company], "people": people}
        created_personas = [persona, *personas.participant_personas(persona)]
    async with pool.acquire() as conn:
        await personas.add_many(conn, created_personas)
        if persona["kind"] == "client":
            await store.enqueue(conn, "refresh_company", {"inn": persona["companies"][0]["inn"]})
    return ok(personas.card(persona, lang))


async def _apply_faults(faults: list[dict]) -> None:
    await _drop("sandbox")
    for f in faults:
        async with _client() as client:
            (await client.post(f"{ADMIN}/mappings", json=fault_stub(f["source"], f["mode"], f.get("inn")))).raise_for_status()


@router.post("/personas/{persona_id}/login", **doc(S.LoginResponse, 404, summary="Войти пользователем из списка"))
async def login(persona_id: str, lang: Lang = "ru", wait_s: WaitS = 5):
    """Войти персоной: включаются отказы её сценария, банк собирает данные её компаний, выдаётся JWT.
    Запросы без токена дальше тоже идут от этой персоны (одна сессия симулятора, docs/08 §2)."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        persona = await personas.get(conn, persona_id)
        if persona is None:
            raise Problem(404, "PERSONA_NOT_FOUND", f"персоны {persona_id} нет")
        await store.kv_set(conn, personas.ACTIVE_KEY, persona_id)
        await store.kv_set(conn, OVERRIDES_KEY, {})
    await _drop("sandbox-event")                             # новый сценарий — мир без событий прошлого
    await _apply_faults(persona["faults"])
    who = actor_of(persona)
    async with pool.acquire() as conn:
        if who.kind == "client":
            await store.enqueue(conn, "refresh_person", {"inn": who.inn})
        companies, loading = await my_companies(conn, who)
        waited = 0.0
        while who.kind == "client" and (loading or not companies) and waited < wait_s:
            await asyncio.sleep(0.25)
            waited += 0.25
            companies, loading = await my_companies(conn, who)
    return ok({"token": auth.issue(persona_id, who.kind), "token_type": "Bearer", "persona": personas.card(persona, lang),
               "actor": {"kind": who.kind, "inn": who.inn, "name": who.name}, "companies": companies,
               "loading": who.kind == "client" and (loading or not companies)})


class LoginIn(BaseModel):
    login: str = Field(min_length=1, max_length=64, description="ID пользователя (s7, R12, bank), ИНН человека или ИНН компании",
                       examples=["s7"])


async def _resolve(conn, login: str) -> dict | None:
    """ID или код пользователя → он; ИНН человека → пользователь с этим человеком; ИНН компании → её пользователь."""
    key = login.strip().lower()
    everyone = await personas.all_personas(conn)
    found = next((p for p in everyone if p["id"].lower() == key), None) or \
        next((p for p in everyone if str(personas.card(p, "ru").get("code", "")).lower() == key), None)
    if found or not key.isdigit():
        return found
    return next((p for p in everyone if p["kind"] == "client" and p["person"]["inn"] == key), None) or \
        await personas.for_company(conn, key)


@auth_router.post("/login", **doc(S.LoginResponse, 404, 422, summary="Вход по ID, ИНН человека или ИНН компании"))
async def login_by_id(body: LoginIn, lang: Lang = "ru", wait_s: WaitS = 5):
    """Вход по ID: тот же результат, что у входа карточкой. Незнакомый ID — 404, выбрать пользователя можно из списка."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        persona = await _resolve(conn, body.login)
    if persona is None:
        raise Problem(404, "USER_NOT_FOUND", "такого пользователя нет — выберите готового или создайте свою компанию",
                      login=body.login)
    return await login(persona["id"], lang, wait_s)


@auth_router.post("/logout", **doc(S.StatusResponse, summary="Выйти"))
async def logout():
    """Выйти: токен на клиенте забывается, запросы без токена снова идут от пользователя по умолчанию."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        await store.kv_delete(conn, personas.ACTIVE_KEY)
    return ok({"status": "ok"})


# ── сценарии по ролям: гид для быстрого прохождения ────────────────────────────────────────────────────────────

BUTTON = {"submit": "submit", "withdraw": "withdraw", "accept": "accept_offer", "decline": "decline_offer", "sign": "sign",
          "answer": "answer_info", "vote": "vote", "bank": "decide", "confirm": "confirm"}
APP = "/api/v1/applications/{application_id}"


def _scenario_api(step, company: dict, request: dict) -> dict:
    """Тот же шаг через API — для Swagger и коллекции запросов."""
    inn = company["inn"]
    match step.action:
        case "create":
            return {"method": "POST", "path": "/api/v1/applications", "body": {"inn": inn, **request, "consent_bki": True}}
        case "run":
            return {"method": "GET", "path": APP, "body": None}
        case "vote":
            return {"method": "POST", "path": f"{APP}/approvals/vote", "body": {"vote": step.arg}}
        case "accept":
            return {"method": "POST", "path": f"{APP}/offer/accept", "body": {"variant": 0}}
        case "sign":
            return {"method": "POST", "path": f"{APP}/signatures", "body": None}
        case "answer":
            body = {"documents": ["Пояснения к отчётности.pdf"]} if step.arg == "documents" else {"corporate_approval": True}
            return {"method": "POST", "path": f"{APP}/info-requests/answer", "body": body}
        case "bank":
            return {"method": "POST", "path": f"/api/v1/bank{APP[7:]}/decision", "body": {"action": step.arg}}
        case "confirm":
            return {"method": "POST", "path": f"/api/v1/bank{APP[7:]}/decision/confirm", "body": {"approve": step.arg}}
        case "event":
            return {"method": "POST", "path": "/api/v1/sandbox/events", "body": {"type": step.arg, "inn": inn}}
        case "forbidden":                            # то же действие, но от того, кому нельзя: ждём 403, а не 422
            return _scenario_api(type(step)(step.user, step.arg, {"confirm": True}.get(step.arg)), company, request)
        case _:
            return {"method": "POST", "path": f"{APP}/{step.action}", "body": None}


@router.get("/scenarios", **doc(S.ScenariosResponse, summary="Сценарии по ролям: кем войти и что нажать"))
async def scenarios(lang: Lang = "ru"):
    """Гид для быстрого прохождения: каждый сценарий — шаги со сменой пользователя, кнопкой, ожидаемым статусом и тем же
    шагом через API. Те же сценарии прокликивает сквозной тест (tests/e2e/test_flows.py) и коллекция запросов."""
    cards = {p["id"]: personas.card(p, lang) for p in personas.presets()}
    companies = {c["key"]: c for c in world.load()["companies"]}
    actions, args = (ACTION_TEXT, ARG_TEXT) if lang == "ru" else (ACTION_TEXT_EN, ARG_TEXT_EN)
    out = []
    for flow in FLOWS:
        company = companies[flow.company]
        request = flow.request or company["scenario"]["request"]
        en = EN[flow.id] if lang == "en" else None
        steps = []
        for n, step in enumerate(flow.steps, 1):
            card = cards.get(step.user)
            user = {"id": step.user, "full_name": card["full_name"], "code": card["code"]} if card else None
            text = actions[step.action] + (f" {args.get(step.arg, step.arg)}" if step.arg is not None else "")
            steps.append({"n": n, "user": user, "action": step.action, "title": text, "button": BUTTON.get(step.action),
                          "api": _scenario_api(step, company, request), "expect_status": step.status,
                          "expect_http": {"forbidden": 403, "create": 201, "event": 202}.get(step.action, 200),
                          "note": en["notes"].get(n, "") if en else step.note})
        out.append({"id": flow.id, "title": en["title"] if en else flow.title, "about": en["about"] if en else flow.about,
                    "company": {"inn": company["inn"], "name": company["name"]},
                    "users": list(dict.fromkeys(s.user for s in flow.steps if s.user != "system")), "steps": steps})
    return ok(out)


# ── отказы, события мира, часы, воркер ───────────────────────────────────────────────────────────────────────────


class FaultIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"source": "bki", "mode": "timeout", "inn": "770100000079"}]})
    source: str = Field(description="ключ из policy/sources.yaml: egrul, bki, debtam… или команда abs")
    mode: Literal["timeout", "error503", "reset", "garbage", "empty"]
    inn: str | None = Field(None, pattern=r"^\d{10}$|^\d{12}$", description="только для этой компании; пусто — для всех")


def fault_stub(source: str, mode: str, inn: str | None) -> dict:
    """Стаб отказа с приоритетом 1 поверх штатного (docs/07 §7)."""
    cfg = source_config()
    targets = {**cfg["sources"], **cfg.get("commands", {})}
    if source not in targets:
        raise Problem(422, "SOURCE_UNKNOWN", f"неизвестный источник {source}", known=sorted(targets))
    return {"priority": 1, "request": match(targets[source], inn), "response": cfg["faults"][mode],
            "metadata": {"createdBy": "sandbox", "source": source, "mode": mode, "inn": inn}}


@router.post("/faults", status_code=201, **doc(S.FaultResponse, 422, status=201, summary="Сломать источник на лету"))
async def add_fault(body: FaultIn):
    """Сломать источник на лету: стаб WireMock с приоритетом 1 поверх штатного ответа, для всех ИНН или одной компании. Продукт
    реагирует, как в бою: ретраи, breaker, политика факта (docs/07)."""
    async with _client() as client:
        resp = await client.post(f"{ADMIN}/mappings", json=fault_stub(body.source, body.mode, body.inn))
        resp.raise_for_status()
    return ok({"id": resp.json()["id"], **body.model_dump()})


@router.get("/faults", **doc(S.FaultsResponse, summary="Активные отказы источников"))
async def list_faults():
    """Отказы источников, которые сейчас включены."""
    async with _client() as client:
        resp = await client.post(f"{ADMIN}/mappings/find-by-metadata",
                                 json={"matchesJsonPath": {"expression": "$.createdBy", "equalTo": "sandbox"}})
        resp.raise_for_status()
    return ok([{"id": m["id"], **m["metadata"]} for m in resp.json().get("mappings", [])])


@router.delete("/faults/{fault_id}", status_code=204, **doc(summary="Снять отказ источника"))
async def remove_fault(fault_id: str):
    """Снять отказ — источник снова отвечает штатно."""
    async with _client() as client:
        await client.delete(f"{ADMIN}/mappings/{fault_id}")


def _director_changed(c: dict, e) -> None:
    """Новый руководитель по ЕГРЮЛ (R12): преемник из описания компании или первый связанный с ней человек."""
    if not world.is_ul(c):
        raise Problem(422, "EVENT_NOT_APPLICABLE", "у ИП нет директора — предприниматель действует сам")
    current = {p for p, _ in c.get("eio", [])}
    successor = c.get("successor") or next((p for p, _ in c.get("access", []) if p not in current), None)
    if not successor or successor in current:
        raise Problem(422, "EVENT_NOT_APPLICABLE", "у компании нет человека, который может стать новым директором")
    c["eio"] = [[successor, c["eio"][0][1] if c.get("eio") else "Генеральный директор"]]
    c.pop("kyc_director", None)                  # руководителя для банка берём из нового ЕГРЮЛ


def _contract_signed(c: dict, e) -> None:
    """Компания выиграла закупку (K5): в ЕИС контракт, где она поставщик, — цена из события или 12 млн ₽, аванс 20%."""
    today = date.fromisoformat(world.load()["today"])
    c["eis"] = [*c.get("eis", []), {"regNum": f"2{c['inn']}{len(c.get('eis', [])) + 1:08d}"[:19],
                                    "customer": "ГБУ «Городской заказчик № 7»", "price": e.amount or 12_000_000,
                                    "signDate": today.isoformat(), "endDate": (today + timedelta(days=240)).isoformat(),
                                    "advancePercent": 20}]


# событие мира → как поменять описание компании и какие источники ответят по-новому
EVENTS = {
    "fns.tax_debt_appeared": (lambda c, e: c["tax"].update(debt=e.amount or 120_000), {"debtam"}),
    "fns.tax_debt_paid": (lambda c, e: c["tax"].update(debt=0), {"debtam"}),
    "legal.bankruptcy_started": (lambda c, e: c.update(flags=sorted({*c.get("flags", []), "bankruptcy"})), {"legal", "bki"}),
    "egrul.unreliable_flag": (lambda c, e: c.update(flags=sorted({*c.get("flags", []), "unreliable_eio"})), {"egrul"}),
    "egrul.liquidation_started": (lambda c, e: c.update(flags=sorted({*c.get("flags", []), "liquidation"})), {"egrul"}),
    "egrul.director_changed": (_director_changed, {"egrul", "bank_access"}),
    "mchd.revoked": (lambda c, e: [poa.update(status="REVOKED") for poa in c.get("poa", [])], {"mchd"}),
    "eis.contract_signed": (_contract_signed, {"eis"}),
}
RECHECK_REASON = {   # почему заявку пересматривают — в событие перехода и в историю заявки
    "fns.tax_debt_appeared": "в ФНС появилась недоимка — пересмотр",
    "fns.tax_debt_paid": "недоимка погашена — пересмотр",
    "legal.bankruptcy_started": "начато банкротство — пересмотр",
    "egrul.unreliable_flag": "в ЕГРЮЛ отметка о недостоверности сведений — пересмотр",
    "egrul.liquidation_started": "компания в ликвидации — пересмотр",
    "egrul.director_changed": "в ЕГРЮЛ новый руководитель — подпись остановлена, полномочия перепроверяются",
    "mchd.revoked": "доверенность отозвана в реестре МЧД — подпись по ней остановлена",
    "eis.contract_signed": "в ЕИС новый госконтракт — данные компании обновлены",
}


class EventIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"type": "egrul.director_changed", "inn": "7701000065"}]})
    type: Literal["fns.tax_debt_appeared", "fns.tax_debt_paid", "legal.bankruptcy_started", "egrul.unreliable_flag",
                  "egrul.liquidation_started", "egrul.director_changed", "mchd.revoked", "eis.contract_signed"] = Field(
        description="что случилось в реестре: недоимка появилась или погашена, банкротство, недостоверность сведений, "
                    "ликвидация, новый директор по ЕГРЮЛ, доверенность отозвана в реестре МЧД, подписан госконтракт в ЕИС")
    inn: str = Field(pattern=r"^\d{10}$|^\d{12}$")
    amount: int | None = Field(None, gt=0, description="сумма: недоимки для fns.tax_debt_appeared, цена контракта для "
                                                       "eis.contract_signed")


async def _company_spec(conn, inn: str) -> tuple[dict, dict]:
    overrides = await store.kv_get(conn, OVERRIDES_KEY, {})
    for persona in await personas.all_personas(conn):
        for c in persona.get("companies", []):
            if c["inn"] == inn:
                return copy.deepcopy(overrides.get(inn) or c), persona["people"]
    raise Problem(404, "COMPANY_NOT_IN_WORLD", f"компании {inn} нет в мире симулятора")


@router.post("/events", status_code=202,
             **doc(S.WorldEventResponse, 404, 422, status=202,
                   summary="Событие в реестре: недоимка, банкротство, новый директор"))
async def world_event(body: EventIn):
    """Событие мира (docs/08 §5): меняется только ответ источника — продукт сам замечает и пересматривает оферты (N17)."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        spec, people = await _company_spec(conn, body.inn)
        change, touched = EVENTS[body.type]
        change(spec, body)
        today = await clock.today(conn)
        errors = world.validate(spec, people, today)
        if errors:
            raise Problem(422, "EVENT_NOT_APPLICABLE", "; ".join(errors), errors=errors)
        overrides = await store.kv_get(conn, OVERRIDES_KEY, {})
        await store.kv_set(conn, OVERRIDES_KEY, {**overrides, body.inn: spec})
    await _import(persona_stubs(spec, people, today, priority=2, created_by="sandbox-event", only=touched))
    async with pool.acquire() as conn:
        await store.add_event(conn, "sandbox.world_event", "sandbox", body.model_dump())
        await store.enqueue(conn, "refresh_company", {"inn": body.inn, "recheck": True, "reason": RECHECK_REASON[body.type]})
    return ok({"event": body.type, "inn": body.inn, "sources": sorted(touched), "recheck": True})


class ClockIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"advance_s": 3600}]})
    advance_s: int = Field(0, ge=0, le=400 * 86400, description="сдвинуть часы вперёд, секунды")
    advance_days: int = Field(0, ge=0, le=400)
    reset: bool = False


async def _clock_view(conn) -> dict:
    return {"offset_s": await clock.offset(conn), "now": await clock.now(conn), "today": await clock.today(conn)}


@router.get("/clock", **doc(S.ClockResponse, summary="Часы мира"))
async def get_clock():
    """Часы мира: сдвиг, текущий момент и дата мира (по умолчанию 21.10.2026)."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        return ok(await _clock_view(conn))


@router.post("/clock", **doc(S.ClockResponse, 422, summary="Перемотать время"))
async def move_clock(body: ClockIn):
    """Перемотка времени: истекают оферты, подписи и дозапросы, просрочивается SLA — без ожидания (docs/08 §5)."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        step = body.advance_s + int(timedelta(days=body.advance_days).total_seconds())
        shift = 0 if body.reset else await clock.offset(conn) + step
        await store.kv_set(conn, clock.OFFSET_KEY, shift)
        return ok(await _clock_view(conn))


@router.post("/reset", **doc(S.StatusResponse, summary="Вернуть мир в исходное состояние"))
async def reset():
    """Вернуть штатный мир: снять отказы, события и свои персоны в WireMock, обнулить часы, снять паузу воркера."""
    async with _client() as client:
        await client.post(f"{ADMIN}/mappings/reset")
        await client.post(f"{ADMIN}/scenarios/reset")
    pool = await store.pool()
    async with pool.acquire() as conn:
        for key, value in (("worker:paused", False), (personas.CUSTOM_KEY, []), (clock.OFFSET_KEY, 0), (OVERRIDES_KEY, {})):
            await store.kv_set(conn, key, value)
        await store.kv_delete(conn, personas.ACTIVE_KEY)
    return ok({"status": "ok"})


@router.post("/worker/{action}", **doc(S.WorkerResponse, 422, summary="Пауза и запуск обработки заявок"))
async def worker(action: Literal["pause", "resume"]):
    """Наш собственный сбой: воркер перестаёт брать задачи, API продолжает работать."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        await store.kv_set(conn, "worker:paused", action == "pause")
    return ok({"paused": action == "pause"})


class WhatIfIn(BaseModel):
    facts: dict = Field(description="факты в формате features.company_facts")
    request: dict = Field(description="{product, amount, term_months, goal, corporate_approval, collateral_value}")
    mode: Literal["simulate", "commit"] = "simulate"


@router.post("/decision", **doc(S.DecisionResponse, 422, summary="Что если: движок на произвольных фактах"))
async def what_if(body: WhatIfIn):
    """Движок на произвольных фактах: «что если» для проверки правил политики."""
    facts = {k: Decimal(str(v)) if k in {"tax_debt", "inflow_avg", "debt_payments", "assets", "revenue", "net_profit"}
             and v is not None else v for k, v in body.facts.items()}
    return ok(engine.decide(facts, body.request, load_policy(), body.mode))
