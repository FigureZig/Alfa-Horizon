"""Пользователи симулятора для экрана входа (docs/08 §2): сценарии из seed/personas.yaml, люди из мира и свои (kv).

Пользователь — человек-клиент или сотрудник банка (кредитный специалист, риск-менеджер) плюс сценарий. Кроме сценариев
в список попадает каждый человек, связанный с компаниями мира: участник ООО, директор по ЕГРЮЛ без доступа в ДБО,
пользователь ДБО без полномочий директора — так можно перелогиниться в любую роль и пройти заявку. Карточку считаем
из мира: права — тем же app/domain/rights.py, профиль — по оборотам и возрасту бизнеса, реестры — по сбоям сценария
и тому, что лежит в источниках. Тексты на ru и en (`?lang=`).
"""

import json
from datetime import date
from decimal import Decimal
from functools import cache, lru_cache

from seed import world

from . import store
from .config import settings
from .domain.rights import rights
from .features import company_facts
from .policy import load as load_policy
from .policy import sources as source_config

CUSTOM_KEY = "users:custom"
ACTIVE_KEY = "session:active_user"
LANGS = ("ru", "en")
_EN_SOURCES = {"bki": "Credit bureau", "bki_info": "Credit bureau", "egrul": "Company register", "egrip": "Sole trader register",
               "girbo": "Financial statements", "legal": "Legal checks", "eis": "Public procurement", "debtam": "Tax arrears"}
T = {
    "ru": {
        "login": "Войти как {name}", "more": " и ещё {n}",
        "profile": "Поступления ≈ {inflow} в месяц, бизнесу {age}", "no_profile": "Данных об оборотах пока нет",
        "all_ok": "Все источники отвечают", "others_ok": "остальные отвечают",
        "fault": {"timeout": "не отвечает", "error503": "ошибка 503", "reset": "обрыв соединения", "garbage": "битый ответ",
                  "empty": "пустой ответ"},
        "owner": "все права, подписывает без доверенности", "eio": "{title} — подписывает без доверенности",
        "eio_joint": "{title} — подписывает вместе с другими руководителями", "eio_blocked": "{title} — подпись заблокирована",
        "poa": "подписывает по МЧД до {date}", "poa_off": "МЧД {status} — подписи нет",
        "poa_status": {"REVOKED": "отозвана", "EXPIRED": "истекла", "SUSPENDED": "приостановлена"},
        "participant": "участник {share}%", "access": {"view": "только просмотр в ДБО", "prepare": "готовит заявки в ДБО",
                                                       "owner": "полный доступ в ДБО", "registry": "без доступа в ДБО"},
        "staff": {"loan_officer": ("Досье и решения по исключениям до {limit}", "Войти как кредитный специалист"),
                  "risk_manager": ("Второй ключ: решения выше {limit}", "Войти как риск-менеджер")},
        "bank_profile": "Отдел кредитования малого бизнеса", "bank_registries": "Все источники по заявке",
        "badge": {"owner": "ИП", "eio": "Директор", "poa": "По доверенности", "participant": "Участник", "prepare": "Сотрудник",
                  "view": "Просмотр", "loan_officer": "Специалист банка", "risk_manager": "Риск-менеджер",
                  "accountant": "Бухгалтер", "owner_member": "Владелец"},
        "role": {"poa_tail": " по доверенности", "share_tail": ", доля {share}%",
                 "owner": "Индивидуальный предприниматель", "eio": "{title} {company}",
                 "eio_share": "{title} {company}, доля {share}%", "poa": "Представитель {company} по доверенности",
                 "participant": "Участник {company}, доля {share}%",
                 "prepare": "Сотрудник {company} с доступом в интернет-банк", "view": "Наблюдатель в интернет-банке {company}"},
        "also": " · ещё {more}", "companies": ("компания", "компании", "компаний"),
        "people": ("сотрудник", "сотрудника", "сотрудников"),
        "about": "{industry}: {staff}, бизнесу {age}", "about_short": "{staff}, бизнесу {age}",
    },
    "en": {
        "login": "Enter as {name}", "more": " and {n} more",
        "profile": "Inflows ≈ {inflow} per month, business is {age} old", "no_profile": "No turnover data yet",
        "all_ok": "All sources respond", "others_ok": "others respond",
        "fault": {"timeout": "times out", "error503": "returns 503", "reset": "drops the connection",
                  "garbage": "returns garbage", "empty": "returns nothing"},
        "owner": "full rights, signs without a power of attorney", "eio": "{title} — signs without a power of attorney",
        "eio_joint": "{title} — signs together with other directors", "eio_blocked": "{title} — signing blocked",
        "poa": "signs by power of attorney until {date}", "poa_off": "power of attorney {status} — cannot sign",
        "poa_status": {"REVOKED": "revoked", "EXPIRED": "expired", "SUSPENDED": "suspended"},
        "participant": "member, {share}%", "access": {"view": "view only in online banking",
                                                      "prepare": "prepares applications in online banking",
                                                      "owner": "full online banking access", "registry": "no online banking"},
        "staff": {"loan_officer": ("Dossiers and decisions on exceptions up to {limit}", "Enter as loan officer"),
                  "risk_manager": ("Second key: decisions above {limit}", "Enter as risk manager")},
        "bank_profile": "Small business lending", "bank_registries": "All sources for an application",
        "badge": {"owner": "Sole trader", "eio": "Director", "poa": "By POA", "participant": "Member", "prepare": "Staff",
                  "view": "Viewer", "loan_officer": "Loan officer", "risk_manager": "Risk manager",
                  "accountant": "Accountant", "owner_member": "Owner"},
        "role": {"poa_tail": " by power of attorney", "share_tail": ", {share}% share",
                 "owner": "Sole proprietor", "eio": "{title}, {company}", "eio_share": "{title}, {company}, {share}% share",
                 "poa": "Representative of {company} by power of attorney", "participant": "Member of {company}, {share}% share",
                 "prepare": "{company} staff with online banking access", "view": "Online banking viewer at {company}"},
        "also": " · {more} more", "companies": ("company", "companies", "companies"), "people": ("person", "people", "people"),
        "about": "{industry}: {staff} on staff, {age} in business", "about_short": "{staff} on staff, {age} in business",
    },
}
_EN_TITLES = {"Генеральный директор": "CEO", "Директор": "Director", "Президент": "President",
              "Управляющий": "Managing director", "Индивидуальный предприниматель": "Sole proprietor",
              "Главный бухгалтер": "Chief accountant", "Финансовый директор": "Finance director", "Владелец": "Owner"}
_TRANSLIT = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
                     ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p", "r", "s", "t", "u",
                      "f", "kh", "ts", "ch", "sh", "shch", "", "y", "", "e", "yu", "ya"], strict=True))


def translit(text: str) -> str:
    out = []
    for ch in text:
        lat = _TRANSLIT.get(ch.lower())
        out.append(ch if lat is None else (lat.capitalize() if ch.isupper() else lat))
    return "".join(out)


def _world_today() -> date:
    return date.fromisoformat(world.load()["today"])


@cache
def _world() -> dict:
    return world.load()


def bank() -> dict:
    return _world()["bank"]


def _linked(companies: list[dict], key: str) -> list[dict]:
    """Компании человека: где он руководитель, участник или пользователь ДБО — сначала где больше прав."""
    rank = {"owner": 0, "eio": 0, "participant": 1}
    found = []
    for c in companies:
        roles = world.registry_roles(c, key)
        level = next((lvl for p, lvl in c["access"] if p == key), None)
        if roles or level:
            found.append((min((rank[r] for r in roles), default=2), c))
    return [c for _, c in sorted(found, key=lambda x: x[0])]


def presets() -> list[dict]:
    """Сценарии из seed/personas.yaml и люди мира без сценария."""
    data = _world()
    people, companies = data["people"], data["companies"]
    by_key = {c["key"]: c for c in companies}
    out, covered = [], set()
    for p in data["presets"]:
        base = {"id": p["id"], "code": p["code"], "title": p["title"], "preview": p["preview"], "about": p.get("about"),
                "listed": p.get("listed", True), "faults": p.get("faults", []), "texts": {}, "custom": False}
        if p.get("kind") == "bank":
            out.append({**base, "kind": "bank", "staff": {"key": p["staff"], **data["staff"][p["staff"]]}})
            continue
        primary = by_key[p["company"]]
        if base["listed"]:                    # человек из скрытого сценария всё равно есть в списке — обычным пользователем
            covered.add(p["person"])
        out.append({**base, "kind": "client", "person": {"key": p["person"], **people[p["person"]]},
                    "companies": [primary, *[c for c in _linked(companies, p["person"]) if c is not primary]], "people": people})
    for key, person in people.items():
        linked = _linked(companies, key)
        if key in covered or not linked:
            continue
        out.append({"id": f"u-{key}", "kind": "client", "person": {"key": key, **person}, "companies": linked, "people": people,
                    "faults": [], "texts": {}, "custom": False, "derived": True, "title": None, "preview": None, "code": None,
                    "about": None, "listed": True})
    return out


def company_personas(owner: dict) -> list[dict]:
    """Все люди своей компании, кроме того, кто её собрал: участники, второй директор, владелец при наёмном директоре,
    бухгалтер, представитель по МЧД — каждый входит под своей карточкой, права у каждого свои."""
    if owner["kind"] != "client" or owner.get("derived"):
        return []
    company, people, main = owner["companies"][0], owner["people"], owner["person"]["key"]
    linked = {key for key, _ in company.get("access", [])} | {poa["person"] for poa in company.get("poa", [])}
    others = [key for key in people if key != main and (key in linked or world.registry_roles(company, key))]
    return [{**owner, "id": f"{owner['id']}-p{index}", "person": {"key": key, **people[key]}, "derived": True, "texts": {}}
            for index, key in enumerate(others, 1)]


async def customs(conn) -> list[dict]:
    saved = await store.kv_get(conn, CUSTOM_KEY, [])
    ids = {persona["id"] for persona in saved}
    result = []
    for persona in saved:
        result.append(persona)
        result.extend(member for member in company_personas(persona) if member["id"] not in ids)
    return result


async def all_personas(conn) -> list[dict]:
    return presets() + await customs(conn)


async def get(conn, persona_id: str) -> dict | None:
    return next((p for p in await all_personas(conn) if p["id"] == persona_id), None)


async def for_company(conn, inn: str) -> dict | None:
    """Кто работает в кабинете компании, если пользователь не назван: сценарий с ней основной, иначе любой связанный."""
    everyone = await all_personas(conn)
    if inn == bank()["inn"]:
        return next((p for p in everyone if p["kind"] == "bank"), None)
    clients = [p for p in everyone if p["kind"] == "client"]
    return next((p for p in clients if p["companies"][0]["inn"] == inn), None) or \
        next((p for p in clients if any(c["inn"] == inn for c in p["companies"])), None)


async def company_names(conn, lang: str = "ru") -> dict[str, str]:
    """ИНН → короткое название всех компаний мира и своих: для реестра заявок банка."""
    return {c["inn"]: (c["name"] if world.is_ul(c) and lang == "ru" else short_name(c, lang))
            for p in await all_personas(conn) for c in p.get("companies", [])}


async def add_many(conn, new_personas: list[dict]) -> None:
    await replace(conn, {persona["id"] for persona in new_personas}, new_personas)


async def replace(conn, old_ids: set[str], new_personas: list[dict]) -> None:
    """Свои пользователи: убрать old_ids и добавить новых — создание, правка компании (её люди меняются) и удаление."""
    await store.kv_set(conn, CUSTOM_KEY, [p for p in await customs(conn) if p["id"] not in old_ids] + new_personas)


async def active_id(conn) -> str:
    return await store.kv_get(conn, ACTIVE_KEY, None) or settings.default_persona


# ── кто есть кто в истории заявки ────────────────────────────────────────────────────────────────────────────────

SYSTEM = {"ru": "Банк", "en": "Bank"}
SYSTEM_DETAIL = {"worker": ("проверка данных", "data check"), "engine": ("автоматическое решение", "automatic decision"),
                 "system": ("пересмотр по новым данным", "recheck on new data"), "timer": ("истёк срок", "deadline passed")}


async def actor_index(conn, lang: str = "ru") -> dict[str, dict]:
    """Метка автора события (client:<ИНН человека>, bank:<id пользователя>) → имя и роль — для истории заявки."""
    index: dict[str, dict] = {}
    for p in await all_personas(conn):
        if p["kind"] == "bank":
            staff = p["staff"]
            index[f"bank:{p['id']}"] = {"kind": "bank", "name": _full_name(staff["fio"], lang), "role": staff["role"],
                                         "title": _loc(staff.get("title") or staff["role"], lang)}
            continue
        for person in (p.get("people") or {}).values():
            index.setdefault(f"client:{person['inn']}", {"kind": "client", "name": _full_name(person["fio"], lang)})
    return index


def actor_view(index: dict, label: str, lang: str = "ru") -> dict:
    """Автор события для людей: клиент и сотрудник — по имени, шаги конвейера и таймер — «Банк» с пояснением."""
    if label in index:
        return index[label]
    detail = SYSTEM_DETAIL.get(label.split(":", 1)[0])
    return {"kind": "system", "name": SYSTEM[lang], "detail": detail[0 if lang == "ru" else 1] if detail else None}


# ── карточка ─────────────────────────────────────────────────────────────────────────────────────────────────────


def _loc(value, lang: str) -> str:
    return value.get(lang) or value.get("ru", "") if isinstance(value, dict) else str(value)


def _first(fio: list[str], lang: str) -> str:
    return fio[1] if lang == "ru" else translit(fio[1])


def _full_name(fio: list[str], lang: str) -> str:
    name = f"{fio[1]} {fio[0]}"
    return name if lang == "ru" else translit(name)


def _money(amount, lang: str) -> str:
    value = Decimal(amount)
    if value >= 1_000_000:
        text = f"{value / 1_000_000:.1f}".rstrip("0").rstrip(".")
        return f"{text.replace('.', ',')} млн ₽" if lang == "ru" else f"₽{text}M"
    text = f"{round(value / 1000):d}"
    return f"{text} тыс. ₽" if lang == "ru" else f"₽{text}K"


def _age(months: int, lang: str) -> str:
    if months < 12:
        return f"{months} мес." if lang == "ru" else f"{months} months"
    years = months // 12
    if lang == "en":
        return f"{years} year{'s' if years != 1 else ''}"
    tail = "лет" if years % 100 in range(11, 15) else {1: "год", 2: "года", 3: "года", 4: "года"}.get(years % 10, "лет")
    return f"{years} {tail}"


def short_name(c: dict, lang: str = "ru") -> str:
    """«Северный Хлеб» для ООО и АО, «ИП Смирнова А. С.» для ИП."""
    if not world.is_ul(c):
        last, *rest = c["name"].removeprefix("ИП ").split()
        if lang == "ru":
            return " ".join(["ИП", last, *(f"{part[0]}." for part in rest)])
        return f"{translit(last)} {''.join(translit(part[0]) + '.' for part in rest[:1])}, sole proprietor"
    inner = c["name"].split("«", 1)[-1].rstrip("»")
    return f"«{inner}»" if lang == "ru" else f"{translit(inner)} {'JSC' if c.get('opf') == 'JSC' else 'LLC'}"


def _organization(companies: list[dict], lang: str) -> str:
    primary = companies[0]
    text = primary["name"] if world.is_ul(primary) and lang == "ru" else short_name(primary, lang)
    if not world.is_ul(primary) and lang == "ru":
        text += f" · {primary['okved'][1][0].lower()}{primary['okved'][1][1:]}"
    return text + (T[lang]["more"].format(n=len(companies) - 1) if len(companies) > 1 else "")


def _role_phrases(r: dict, lang: str) -> list[str]:
    t, out, kinds = T[lang], [], {x["role"] for x in r["roles"]}
    for role in r["roles"]:
        match role["role"]:
            case "owner":
                out.append(t["owner"])
            case "eio":
                title = role["title"] if lang == "ru" else _EN_TITLES.get(role["title"], translit(role["title"]))
                key = "eio_blocked" if role["blocked"] else ("eio_joint" if role["mode"] == "joint" else "eio")
                out.append(t[key].format(title=title[0].lower() + title[1:] if lang == "ru" else title))
            case "participant":
                out.append(t["participant"].format(share=f"{role['share']:g}"))
            case "poa":
                y, m, d = role["valid_to"].split("-")
                until = f"{d}.{m}.{y}" if lang == "ru" else role["valid_to"]
                out.append(t["poa"].format(date=until) if role["status"] == "ACTIVE"
                           else t["poa_off"].format(status=t["poa_status"].get(role["status"], role["status"])))
            case "bank_access" if not kinds & {"owner", "eio"}:
                out.append(t["access"].get(role["level"], role["level"]))
    return out


def _permissions(companies: list[dict], rights_list: list[dict], lang: str) -> str:
    parts = [", ".join(_role_phrases(r, lang)) or T[lang]["access"]["registry"] for r in rights_list]
    if len(companies) == 1:
        text = parts[0]
    else:
        text = "; ".join(f"{short_name(c, lang)}: {p}" for c, p in zip(companies, parts, strict=True))
    return text[:1].upper() + text[1:]


def _registries(faults: list[dict], lang: str) -> str:
    """Какие источники отвечают. Что найдено в реестрах (недоимка, расхождения), на экране входа не раскрываем —
    это банк покажет в кабинете и в решении, иначе карточка подсказывает исход."""
    t, names, notes = T[lang], source_config()["sources"], []
    for f in faults:
        name = names[f["source"]]["name"] if lang == "ru" else _EN_SOURCES.get(f["source"], f["source"])
        notes.append(f"{name}: {t['fault'][f['mode']]}")
    if faults:
        notes.append(t["others_ok"])
    return "; ".join(notes) if notes else t["all_ok"]


def _plural(n: int, forms: tuple[str, str, str], lang: str) -> str:
    if lang == "en":
        return f"{n} {forms[0] if n == 1 else forms[1]}"
    k = 0 if n % 10 == 1 and n % 100 != 11 else 1 if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else 2
    return f"{n} {forms[k]}"


def _about(facts: dict, lang: str) -> str:
    """Чем занимается компания, простым языком: вид деятельности, сколько людей, сколько лет бизнесу."""
    t = T[lang]
    staff = _plural(facts.get("headcount") or 1, t["people"], lang)
    age = _age(facts.get("age_months") or 0, lang)
    industry = facts.get("okved_name") if lang == "ru" else None
    return t["about"].format(industry=industry, staff=staff, age=age) if industry else t["about_short"].format(staff=staff,
                                                                                                                age=age)


def _role(persona: dict, main_rights: dict, lang: str) -> tuple[str, str]:
    """Значок роли и кто этот человек в основной компании — из реестров и ДБО, как и права."""
    t, roles = T[lang], {r["role"]: r for r in main_rights["roles"]}
    companies = persona["companies"]
    company = short_name(companies[0], lang)
    share = roles.get("participant", {}).get("share")
    if "owner" in roles:
        key, text = "owner", t["role"]["owner"]
    elif "eio" in roles:
        title = roles["eio"]["title"] if lang == "ru" else _EN_TITLES.get(roles["eio"]["title"], roles["eio"]["title"])
        key = "eio"
        text = t["role"]["eio_share" if share is not None else "eio"].format(title=title, company=company,
                                                                             share=f"{share:g}" if share else "")
    elif "poa" in roles and main_rights["sign_mode"] == "poa":
        key, text = "poa", t["role"]["poa"].format(company=company)
    elif "participant" in roles:
        key, text = "participant", t["role"]["participant"].format(company=company, share=f"{share:g}")
    else:
        key = "prepare" if main_rights["can"]["prepare"] else "view"
        text = t["role"][key].format(company=company)
    raw = (companies[0].get("titles") or {}).get(persona["person"]["key"])      # должность в своей компании
    if raw and key in ("poa", "participant", "prepare", "view"):
        key = {"Главный бухгалтер": "accountant", "Владелец": "owner_member"}.get(raw, key)
        tail = t["role"]["poa_tail"] if "poa" in roles and main_rights["sign_mode"] == "poa" else ""
        tail += t["role"]["share_tail"].format(share=f"{share:g}") if share is not None else ""
        text = f"{raw if lang == 'ru' else _EN_TITLES.get(raw, raw)} {company}{tail}"
    if len(companies) > 1:
        text += t["also"].format(more=_plural(len(companies) - 1, t["companies"], lang))
    return t["badge"][key], text


@cache
def _demo_facts(inn: str) -> dict:
    data = _world()
    company = next(c for c in data["companies"] if c["inn"] == inn)
    return company_facts(inn, world.served(company, data["people"], _world_today()), _world_today())


@lru_cache(maxsize=256)
def _custom_facts(blob: str) -> dict:
    company, people = json.loads(blob)
    return company_facts(company["inn"], world.served(company, people, _world_today()), _world_today())


def custom_facts(company: dict, people: dict) -> dict:
    """Факты своей компании из её описания. Считаем один раз на все её входы и на предпросмотр конструктора: ключ —
    содержимое, а не ИНН (после правки или сброса мира тот же ИНН может получить другая компания). Не изменять."""
    return _custom_facts(json.dumps([company, people], sort_keys=True, ensure_ascii=False))


def _facts(persona: dict, company: dict) -> dict:
    return custom_facts(company, persona["people"]) if persona["custom"] else _demo_facts(company["inn"])


def card(persona: dict, lang: str = "ru") -> dict:
    """Карточка в контракте фронта (SandboxPersonaDto) плюс ИНН и компании для входа."""
    lang = lang if lang in LANGS else "ru"
    t = T[lang]
    out = {"id": persona["id"], "kind": persona["kind"], "faults": persona["faults"], "custom": persona["custom"]}
    if persona["kind"] == "bank":
        staff = persona["staff"]
        permissions, login = t["staff"][staff["role"]]
        permissions = permissions.format(limit=_money(load_policy()["params"]["specialist_authority_max"], lang))
        org = bank()["name"] if lang == "ru" else bank()["name_en"]
        role_title = f"{_loc(staff.get('title') or staff['role'], lang)} · {org}"
        about = _loc(persona["about"], lang) if persona.get("about") else permissions
        out.update(badge=t["badge"][staff["role"]], role_title=role_title, about=about,
                   full_name=_full_name(staff["fio"], lang), organization=role_title, role=staff["role"],
                   permissions=permissions, profile=t["bank_profile"],
                   registries=t["bank_registries"], login_label=login, inn=bank()["inn"], person_inn=None,
                   company_inn=None, companies=[])
    else:
        person, companies = persona["person"], persona["companies"]
        facts_list = [_facts(persona, c) for c in companies]
        rights_list = [rights(person["inn"], f) for f in facts_list]
        main = facts_list[0]
        profile = t["profile"].format(inflow=_money(main["inflow_avg"], lang), age=_age(main["age_months"], lang)) \
            if main.get("inflow_avg") else t["no_profile"]
        badge, role_title = _role(persona, rights_list[0], lang)
        about = _loc(persona["about"], lang) if persona.get("about") else _about(main, lang)
        out.update(badge=badge, role_title=role_title, about=about, role="client",
                   full_name=_full_name(person["fio"], lang), organization=_organization(companies, lang),
                   permissions=_permissions(companies, rights_list, lang), profile=profile,
                   registries=_registries(persona["faults"], lang),
                   login_label=t["login"].format(name=_first(person["fio"], lang)), inn=companies[0]["inn"],
                   person_inn=person["inn"], company_inn=companies[0]["inn"],
                   companies=[{"inn": c["inn"], "name": c["name"]} for c in companies])
    # прежние поля контракта фронта (SandboxPersonaDto): code — значок роли, scenario — кто это, preview — о компании
    out.update(code=out["badge"], scenario=out["role_title"], preview=out["about"])
    out.update({k: v for k, v in (persona.get("texts") or {}).items() if v})   # тексты из конструктора фронта важнее
    return out
