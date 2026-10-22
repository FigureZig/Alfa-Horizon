"""Пользователи симулятора для экрана входа (docs/08 §2): сценарии из seed/personas.yaml, люди из мира и свои (kv).

Пользователь — человек-клиент или сотрудник банка (кредитный специалист, риск-менеджер) плюс сценарий. Кроме сценариев
в список попадает каждый человек, связанный с компаниями мира: участник ООО, директор по ЕГРЮЛ без доступа в ДБО,
пользователь ДБО без полномочий директора — так можно перелогиниться в любую роль и пройти заявку. Карточку считаем
из мира: права — тем же app/domain/rights.py, профиль — по оборотам и возрасту бизнеса, реестры — по сбоям сценария
и тому, что лежит в источниках. Тексты на ru и en (`?lang=`).
"""

from datetime import date
from decimal import Decimal
from functools import cache

from seed import world

from . import store
from .config import settings
from .domain.rights import rights
from .features import company_facts
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
        "tax_debt": "ФНС: недоимка {amount}", "liquidation": "ЕГРЮЛ: ликвидация", "bankruptcy": "банкротство",
        "unreliable": "ЕГРЮЛ: сведения о руководителе недостоверны", "disqualified": "ЕГРЮЛ: руководитель дисквалифицирован",
        "conflict": "ЕГРЮЛ и анкета банка: разные руководители", "contract": "ЕИС: контракт на {amount}",
        "owner": "все права, подписывает без доверенности", "eio": "{title} — подписывает без доверенности",
        "eio_joint": "{title} — подписывает вместе с другими руководителями", "eio_blocked": "{title} — подпись заблокирована",
        "poa": "подписывает по МЧД до {date}", "poa_off": "МЧД {status} — подписи нет",
        "poa_status": {"REVOKED": "отозвана", "EXPIRED": "истекла", "SUSPENDED": "приостановлена"},
        "participant": "участник {share}%", "access": {"view": "только просмотр в ДБО", "prepare": "готовит заявки в ДБО",
                                                       "owner": "полный доступ в ДБО", "registry": "без доступа в ДБО"},
        "staff": {"loan_officer": ("Досье и решения по исключениям до {limit}", "Войти как кредитный специалист"),
                  "risk_manager": ("Второй ключ: решения выше {limit}", "Войти как риск-менеджер")},
        "bank_profile": "Отдел кредитования малого бизнеса", "bank_registries": "Все источники по заявке",
        "derived": {
            "participant": ("Участник {company} с долей {share}%",
                            "Голосует за крупную сделку, когда банк просит согласие участников", "Участник"),
            "eio": ("Директор {company}", "Подписывает договоры, которые подготовили другие пользователи компании", "Директор"),
            "poa": ("Представитель {company} по МЧД", "Готовит заявки и подписывает кредитный договор по доверенности", "МЧД"),
            "prepare": ("Пользователь ДБО {company}", "Готовит и подаёт заявки, но подписывать не вправе", "ДБО"),
            "view": ("Наблюдатель в ДБО {company}", "Видит компанию и заявки, но ничего не меняет", "Просмотр"),
        },
    },
    "en": {
        "login": "Enter as {name}", "more": " and {n} more",
        "profile": "Inflows ≈ {inflow} per month, business is {age} old", "no_profile": "No turnover data yet",
        "all_ok": "All sources respond", "others_ok": "others respond",
        "fault": {"timeout": "times out", "error503": "returns 503", "reset": "drops the connection",
                  "garbage": "returns garbage", "empty": "returns nothing"},
        "tax_debt": "Tax arrears of {amount}", "liquidation": "Company register: liquidation", "bankruptcy": "bankruptcy",
        "unreliable": "Company register: director data marked unreliable",
        "disqualified": "Company register: director disqualified",
        "conflict": "Register and bank records name different directors", "contract": "Public contract for {amount}",
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
        "derived": {
            "participant": ("Member of {company} with a {share}% share", "Votes on a major transaction when the bank asks "
                            "for the members' consent", "Member"),
            "eio": ("Director of {company}", "Signs agreements prepared by other company users", "Director"),
            "poa": ("Representative of {company} by power of attorney",
                    "Prepares applications and signs the loan agreement by power of attorney", "POA"),
            "prepare": ("Online banking user of {company}", "Prepares and submits applications but may not sign", "Banking"),
            "view": ("Viewer in online banking of {company}", "Sees the company and applications, changes nothing", "Viewer"),
        },
    },
}
_EN_TITLES = {"Генеральный директор": "CEO", "Директор": "Director", "Президент": "President",
              "Управляющий": "Managing director", "Индивидуальный предприниматель": "Sole proprietor"}
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
        base = {"id": p["id"], "code": p["code"], "title": p["title"], "preview": p["preview"],
                "faults": p.get("faults", []), "texts": {}, "custom": False}
        if p.get("kind") == "bank":
            out.append({**base, "kind": "bank", "staff": {"key": p["staff"], **data["staff"][p["staff"]]}})
            continue
        primary = by_key[p["company"]]
        covered.add(p["person"])
        out.append({**base, "kind": "client", "person": {"key": p["person"], **people[p["person"]]},
                    "companies": [primary, *[c for c in _linked(companies, p["person"]) if c is not primary]], "people": people})
    for key, person in people.items():
        linked = _linked(companies, key)
        if key in covered or not linked:
            continue
        out.append({"id": f"u-{key}", "kind": "client", "person": {"key": key, **person}, "companies": linked, "people": people,
                    "faults": [], "texts": {}, "custom": False, "derived": True, "title": None, "preview": None, "code": None})
    return out


async def customs(conn) -> list[dict]:
    return await store.kv_get(conn, CUSTOM_KEY, [])


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


async def add(conn, persona: dict) -> None:
    await store.kv_set(conn, CUSTOM_KEY, [p for p in await customs(conn) if p["id"] != persona["id"]] + [persona])


async def active_id(conn) -> str:
    return await store.kv_get(conn, ACTIVE_KEY, None) or settings.default_persona


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


def _registries(faults: list[dict], facts_list: list[dict], companies: list[dict], lang: str) -> str:
    t, names, notes = T[lang], source_config()["sources"], []
    for f in faults:
        name = names[f["source"]]["name"] if lang == "ru" else _EN_SOURCES.get(f["source"], f["source"])
        notes.append(f"{name}: {t['fault'][f['mode']]}")
    if faults:
        notes.append(t["others_ok"])
    for c, f in zip(companies, facts_list, strict=True):
        found = []
        if f.get("tax_debt"):
            found.append(t["tax_debt"].format(amount=_money(f["tax_debt"], lang)))
        found += [t[k] for k in ("liquidation", "bankruptcy") if f.get(k)]
        found += [t[k] for k in ("unreliable", "disqualified") if any(e.get(k) for e in f.get("eio", []))]
        found += [t["conflict"]] * bool(f.get("conflicts"))
        found += [t["contract"].format(amount=_money(k["price"], lang)) for k in f.get("contracts", [])]
        notes += [f"{short_name(c, lang)}: {n}" if len(companies) > 1 else n for n in found]
    return "; ".join(notes) if notes else t["all_ok"]


@cache
def _demo_facts(inn: str) -> dict:
    data = _world()
    company = next(c for c in data["companies"] if c["inn"] == inn)
    return company_facts(inn, world.served(company, data["people"], _world_today()), _world_today())


def _facts(persona: dict, company: dict) -> dict:
    if not persona["custom"]:
        return _demo_facts(company["inn"])
    return company_facts(company["inn"], world.served(company, persona["people"], _world_today()), _world_today())


def _derived_texts(persona: dict, main_rights: dict, lang: str) -> tuple[str, str, str]:
    """Сценарий для человека без сценария — по его главной роли в основной компании."""
    roles = {r["role"]: r for r in main_rights["roles"]}
    company = short_name(persona["companies"][0], lang)
    if "eio" in roles or "owner" in roles:
        key, share = "eio", None
    elif "participant" in roles:
        key, share = "participant", roles["participant"]["share"]
    elif "poa" in roles and main_rights["sign_mode"] == "poa":
        key, share = "poa", None
    else:
        key, share = ("prepare" if main_rights["can"]["prepare"] else "view"), None
    title, preview, code = T[lang]["derived"][key]
    return title.format(company=company, share=f"{share:g}" if share is not None else ""), preview, code


def card(persona: dict, lang: str = "ru", *, limit=None) -> dict:
    """Карточка в контракте фронта (SandboxPersonaDto) плюс ИНН и компании для входа."""
    lang = lang if lang in LANGS else "ru"
    t = T[lang]
    out = {"id": persona["id"], "kind": persona["kind"], "faults": persona["faults"], "custom": persona["custom"]}
    if persona["kind"] == "bank":
        staff = persona["staff"]
        permissions, login = t["staff"][staff["role"]]
        org = bank()["name"] if lang == "ru" else bank()["name_en"]
        out.update(code=_loc(persona["code"], lang), scenario=_loc(persona["title"], lang),
                   preview=_loc(persona["preview"], lang), full_name=_full_name(staff["fio"], lang),
                   organization=f"{_loc(staff['title'], lang)} · {org}", role=staff["role"],
                   permissions=permissions.format(limit=_money(limit, lang) if limit else "—"), profile=t["bank_profile"],
                   registries=t["bank_registries"], login_label=login, inn=bank()["inn"], person_inn=None,
                   company_inn=None, companies=[])
    else:
        person, companies = persona["person"], persona["companies"]
        facts_list = [_facts(persona, c) for c in companies]
        rights_list = [rights(person["inn"], f) for f in facts_list]
        main = facts_list[0]
        profile = t["profile"].format(inflow=_money(main["inflow_avg"], lang), age=_age(main["age_months"], lang)) \
            if main.get("inflow_avg") else t["no_profile"]
        if persona.get("derived"):
            scenario, preview, code = _derived_texts(persona, rights_list[0], lang)
        else:
            scenario, preview, code = _loc(persona["title"], lang), _loc(persona["preview"], lang), _loc(persona["code"], lang)
        out.update(code=code, scenario=scenario, preview=preview, role="client",
                   full_name=_full_name(person["fio"], lang), organization=_organization(companies, lang),
                   permissions=_permissions(companies, rights_list, lang), profile=profile,
                   registries=_registries(persona["faults"], facts_list, companies, lang),
                   login_label=t["login"].format(name=_first(person["fio"], lang)), inn=companies[0]["inn"],
                   person_inn=person["inn"], company_inn=companies[0]["inn"],
                   companies=[{"inn": c["inn"], "name": c["name"]} for c in companies])
    out.update({k: v for k, v in (persona.get("texts") or {}).items() if v})   # тексты из конструктора фронта важнее
    return out
