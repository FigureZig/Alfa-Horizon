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

from .. import auth, clock, company, personas, store
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
    """Пользователи для экрана входа простым языком: кто это (`role_title`), чем занимается компания (`about`), значок роли
    (`badge`). Без сценариев и исходов: сценарии со сменой ролей — в документации и `GET /sandbox/scenarios`. Скрытые
    сценарии отказов (`n1`, `n2`) и дубли входят по ID, но в списке их нет."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        items = await personas.all_personas(conn)
    return ok([personas.card(p, lang) for p in items if p.get("listed", True)])


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
    # простыми вопросами (каталог ответов — GET /sandbox/persona-options): из них генератор строит выписку, отчётность и людей
    industry: Literal[tuple(world.INDUSTRIES)] | None = Field(None, description="чем занимается: отрасль из каталога — "
                                                                                "ОКВЭД, сезонность и кто платит по умолчанию")
    structure: Literal[world.STRUCTURES] | None = Field(None, description="как устроена компания: от неё — кто подписывает и "
                                                                         "кто одобряет крупную сделку")
    accountant: bool = Field(False, description="есть бухгалтер: готовит заявки в ДБО, подписать не может")
    representative: bool = Field(False, description="есть представитель по МЧД: подписывает кредитный договор (не у ИП)")
    seasonality: Literal["flat", "summer", "year_end", "harvest"] | None = Field(None, description="когда выручки больше")
    stability: Literal["steady", "uneven", "volatile"] | None = Field(None, description="насколько ровная выручка")
    trend: Literal["growing", "stable", "declining"] | None = Field(None, description="как выручка менялась за 3 месяца")
    channel: Literal["cards", "invoices", "marketplace", "government"] | None = Field(None, description="кто и как платит")
    loans: Literal["none", "some", "heavy"] | None = Field(None, description="кредиты в других банках")
    delays: Literal["none", "recent", "serious"] | None = Field(None, description="просрочки по кредитам")
    # точные цифры — если нужны (иначе их выведет генератор из ответов выше)
    okved: str = Field("62.01", pattern=r"^\d{2}(\.\d{1,2}){0,2}$", description="ОКВЭД 2, если отрасли нет в каталоге")
    okved_name: str = Field("Основной вид деятельности", max_length=300, description="название вида деятельности")
    age_months: int = Field(36, ge=1, le=600, description="сколько месяцев бизнесу")
    headcount: int = Field(12, ge=1, le=250, description="сотрудников — от численности категория МСП")
    inflow_avg: int = Field(3_000_000, ge=10_000, description="выручка: средние поступления на счёт в месяц, ₽")
    inflow_cv: float | None = Field(None, ge=0, le=1, description="разброс поступлений от месяца к месяцу (вместо stability)")
    inflow_trend: float | None = Field(None, ge=-0.9, le=1, description="последние 3 месяца к предыдущим 9, минус 1")
    debt_load: float | None = Field(None, ge=0, le=1, description="платежи по текущим кредитам / поступления (вместо loans)")
    overdue_days: int | None = Field(None, ge=0, le=365, description="максимальная просрочка в КИ (вместо delays)")
    bki_requests: int | None = Field(None, ge=0, le=50, description="запросы в БКИ за 30 дней")
    tax_debt: int | None = Field(None, ge=0, description="недоимка, ₽")
    participants: int | None = Field(None, ge=1, le=10, description="участников ООО (для partners — от двух)")
    profit_margin: float | None = Field(None, ge=-1, le=1, description="чистая прибыль / выручка")
    contract_price: int | None = Field(None, gt=0, description="действующий госконтракт в ЕИС, ₽")
    flags: list[str] = Field([], description="флаги из каталога GET /sandbox/persona-options: недоимка, банкротство, "
                             "просрочка, крупная сделка, БКИ не отвечает… Задают параметры поверх полей и обязаны менять решение",
                             examples=[["tax_debt", "bki_down"]])


TEXT_FIELDS = ("organization", "scenario", "permissions", "profile", "registries", "preview", "login_label")
PARAMS = ("form", "okved", "okved_name", "age_months", "headcount", "inflow_avg", "inflow_cv", "inflow_trend", "debt_load",
          "overdue_days", "bki_requests", "tax_debt", "participants", "profit_margin", "contract_price")
FORMS = {"IP": {"ru": "ИП", "en": "Sole proprietor"}, "LLC": {"ru": "ООО", "en": "LLC"}, "JSC": {"ru": "АО", "en": "JSC"}}
# простые ответы конструктора → параметры генератора (seed/world.py)
TREND = {"growing": 0.15, "stable": 0.0, "declining": -0.25}
LOANS = {"none": 0.0, "some": 0.15, "heavy": 0.45}          # платежи по кредитам — доля выручки
DELAYS = {"none": 0, "recent": 20, "serious": 120}           # самая долгая просрочка, дней
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
CHOICES = {   # id → (ru, en)
    "seasonality": {"flat": ("Ровно круглый год", "Even all year"), "summer": ("Летом больше", "More in summer"),
                    "year_end": ("Больше к концу года", "More towards the year end"),
                    "harvest": ("После урожая", "After the harvest")},
    "stability": {"steady": ("Стабильно", "Steady"), "uneven": ("Бывают провалы", "Some dips"),
                  "volatile": ("Сильно скачет", "Very uneven")},
    "trend": {"growing": ("Растёт", "Growing"), "stable": ("Без изменений", "Stable"), "declining": ("Падает", "Declining")},
    "channel": {"cards": ("Покупатели платят картами", "Customers pay by card"),
                "invoices": ("Компании платят по счетам", "Companies pay invoices"),
                "marketplace": ("Выплаты маркетплейса", "Marketplace payouts"), "government": ("Госзаказ", "Public contracts")},
    "loans": {"none": ("Кредитов нет", "No loans"), "some": ("Есть кредит: платёж около 15% выручки", "A loan: ~15% of revenue"),
              "heavy": ("Кредиты съедают почти половину выручки", "Loans take almost half of revenue")},
    "delays": {"none": ("Без просрочек", "No delays"), "recent": ("Была просрочка до месяца", "A delay of up to a month"),
               "serious": ("Просрочка больше 90 дней", "A delay of over 90 days")},
}
STRUCTURE_TEXTS = {   # как устроена компания → кто подписывает и кто одобряет крупную сделку, с нормой
    "owner_director": ("Владелец и директор — один человек", "Owner and director are one person",
                       "Согласия на крупную сделку не нужно: единственный участник сам руководит (14-ФЗ ст. 46 п. 7)"),
    "hired_director": ("Владелец нанял директора", "The owner hired a director",
                       "Крупную сделку одобряет владелец письменным решением (14-ФЗ ст. 39, ст. 46 п. 3)"),
    "partners": ("Несколько участников", "Several members",
                 "Крупную сделку одобряет общее собрание: голоса по долям, нужно больше половины (14-ФЗ ст. 46 п. 3)"),
    "two_directors_joint": ("Два директора, подписывают вместе", "Two directors who sign together",
                            "Договор подписывают оба директора (ГК ст. 53 п. 1)"),
    "two_directors_independent": ("Два директора, каждый сам", "Two directors, each on their own",
                                  "Договор вправе подписать любой из директоров (ГК ст. 53 п. 1)"),
}
STRUCTURE_FORMS = {k: ["LLC", "JSC"] if k == "owner_director" else ["LLC"] for k in STRUCTURE_TEXTS}   # у ИП — он сам
PEOPLE_TEXTS = {
    "accountant": ("Бухгалтер готовит заявки", "An accountant prepares applications",
                   "Доступ в ДБО на подготовку: готовит и подаёт заявку, подписать не может"),
    "representative": ("Финансовый директор по доверенности", "A finance director by power of attorney",
                       "Машиночитаемая доверенность на подписание кредитного договора (ГК ст. 185.1; 63-ФЗ ст. 17.2)"),
}


def _param(name: str) -> dict:
    field = PersonaIn.model_fields[name]
    bounds = {type(m).__name__.lower(): getattr(m, type(m).__name__.lower()) for m in field.metadata
              if type(m).__name__ in ("Ge", "Le", "Gt")}
    base = field.annotation.__args__[0] if getattr(field.annotation, "__args__", None) else field.annotation
    kind = {int: "integer", float: "number", str: "string"}.get(base, "string")
    if name == "form":
        kind = "enum"
    return {"id": name, "type": kind, "default": field.default, "description": field.description, **bounds}


def _choices(name: str, lang: str) -> list[dict]:
    i = 0 if lang == "ru" else 1
    return [{"id": k, "title": v[i]} for k, v in CHOICES[name].items()]


@router.get("/persona-options", **doc(S.PersonaOptionsResponse, summary="Своя компания: вопросы, ответы и особенности"))
async def persona_options(lang: Lang = "ru"):
    """Что спросить, чтобы собрать свою компанию простым языком: чем занимается (отрасль с ОКВЭД), как устроена (кто
    подписывает и кто одобряет крупную сделку — с нормой), как платят клиенты и как ведёт себя выручка, кредиты и
    просрочки. Особенности (недоимка, банкротство, сбой БКИ…) — фактами; что они значат для кредита, покажет решение банка.
    Точные цифры (params) — для тех, кому нужно задать их самому."""
    cat, i = flags.catalog(), 0 if lang == "ru" else 1
    return ok({"forms": [{"id": k, "title": v[lang]} for k, v in FORMS.items()],
               "industries": [{"id": k, "title": INDUSTRY_TITLES[k][i], "okved": code, "okved_name": name,
                               "seasonality": world.PROFILES[profile]["season"], "channel": world.PROFILES[profile]["channel"]}
                              for k, (code, name, profile) in world.INDUSTRIES.items()],
               "structures": [{"id": k, "title": t[i], "means": t[2], "forms": STRUCTURE_FORMS[k]}
                              for k, t in STRUCTURE_TEXTS.items()],
               "people": [{"id": k, "title": t[i], "means": t[2], "forms": ["LLC", "JSC"] if k == "representative"
                           else ["IP", "LLC", "JSC"]} for k, t in PEOPLE_TEXTS.items()],
               "choices": {name: _choices(name, lang) for name in CHOICES},
               "groups": [{"id": k, "title": v[lang]} for k, v in cat["groups"].items()],
               "flags": [{"id": k, "group": f["group"], "title": f["title"][lang], "effect": f["effect"][lang],
                          "forms": f["forms"]} for k, f in cat["flags"].items()],
               "params": [_param(name) for name in PARAMS]})


def _spec(body: PersonaIn, form: str, inn: str | None) -> dict:
    """Ответы конструктора → описание компании для генератора: простые ответы, точные цифры поверх них."""
    numbers = {k: v for k, v in body.model_dump(include={"age_months", "headcount", "inflow_avg", "inflow_cv", "inflow_trend",
                                                         "debt_load", "overdue_days", "bki_requests", "tax_debt",
                                                         "participants", "profit_margin", "contract_price"}).items()
               if v is not None}
    code, name, profile = world.INDUSTRIES[body.industry] if body.industry else (body.okved, body.okved_name,
                                                                                world.profile_for(body.okved))
    spec = {"kind": form, "inn": inn, "okved": [code, name], "profile": profile, "owner_fio": parse_fio(body.full_name),
            "company_name": company_title(body.organization) if form != "IP" else None,
            "accountant": body.accountant, "representative": body.representative and form != "IP"}
    spec.update({k: v for k, v in (("structure", body.structure), ("seasonality", body.seasonality),
                                   ("stability", body.stability), ("channel", body.channel)) if v})
    if body.trend:
        spec["inflow_trend"] = TREND[body.trend]
    if body.loans:
        spec["debt_load"] = LOANS[body.loans]
    if body.delays:
        spec["overdue_days"] = DELAYS[body.delays]
    return {**spec, **numbers}                      # точная цифра важнее ответа «примерно»


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
    if body.kind == "client" and form == "IP" and (body.structure not in (None, "owner_director") or body.representative):
        raise Problem(422, "STRUCTURE_NOT_APPLICABLE", "у ИП нет участников и директоров, а доверенность ИП не моделируем — "
                      "предприниматель действует сам (ГК ст. 23)", form=form)
    if body.kind == "client" and form != "IP" and body.structure and form not in STRUCTURE_FORMS[body.structure]:
        raise Problem(422, "STRUCTURE_NOT_APPLICABLE", "у АО акционеров ведёт реестродержатель, а не ЕГРЮЛ: участников и "
                      "одобрение сделки по ним не моделируем — для АО только «Владелец и директор — один человек»",
                      form=form, structure=body.structure)
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
        title = body.organization or "Кредитный специалист"
        role = "risk_manager" if "риск" in title.lower() or "risk" in title.lower() else "loan_officer"   # роль — код
        persona = {**base, "id": f"b{seq}", "kind": "bank", "staff": {"key": f"staff{seq}", "fio": fio, "role": role,
                                                                       "title": {"ru": title, "en": title}}}
        created_personas = [persona]
    else:
        spec, base["faults"] = flags.apply(_spec(body, form, inn), body.flags)
        if spec.get("structure") in ("owner_director", "hired_director") and spec.get("participants", 1) > 1 \
                or spec.get("structure") == "partners" and spec.get("participants", 2) < 2:
            raise Problem(422, "STRUCTURE_CONFLICT", "устройство компании и число участников противоречат друг другу: при "
                          "одном владельце участник один, у «нескольких участников» — от двух", structure=spec["structure"],
                          participants=spec.get("participants"), flags=body.flags)
        company, people = world.custom(spec, number, today)
        errors = world.validate(company, people, today)
        if errors:
            raise Problem(422, "PERSONA_INVALID", "такой компании не бывает: " + "; ".join(errors), errors=errors)
        await _import(persona_stubs(company, people, today))
        owner = company.get("owner") or company["eio"][0][0]
        persona = {**base, "id": f"c{seq}", "kind": "client", "person": {"key": owner, **people[owner]},
                   "companies": [company], "people": people}
        created_personas = [persona, *personas.company_personas(persona)]
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
        next((p for p in everyone if isinstance(p.get("code"), str) and p["code"].lower() == key), None)   # S7, R12
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
        # выданные кредиты остаются в истории заявок, но мир — как сначала: прогноз и предложения их больше не учитывают
        await company.forget_loans(conn)
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
