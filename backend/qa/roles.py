"""Роли и статусы: uv run python -m qa.roles → docs/15_roles.md

Матрица «статус × роль» строится из lifecycle.actions и таблицы переходов, пользователи — из personas, сценарии —
из seed/flows.py (их же прокликивает tests/e2e/test_flows.py). Руками файл не правят; детерминирован.
"""

from pathlib import Path

from app import lifecycle, personas
from app.domain.state import EDGES, STATUSES, TERMINAL
from app.policy import load
from seed import flags
from seed.flows import ACTION_TEXT, ARG_TEXT, FLOWS

OUT = Path(__file__).resolve().parents[2] / "docs" / "15_roles.md"
ACTIONS = {"submit": "подать", "withdraw": "отозвать", "accept_offer": "принять оферту", "decline_offer": "отказаться от оферты",
           "answer_info": "ответить на запрос", "sign": "подписать", "vote": "голосовать",
           "decide": "одобрить · отказать · дозапросить", "confirm": "подтвердить или вернуть (второй ключ)"}
KIND = {"system": "конвейер", "timer": "таймер"}
P = "770000000001"                  # условный участник для матрицы
ROLES = [   # колонка → (кто это, откуда роль, права для lifecycle.actions)
    ("Руководитель или ИП", "ЕГРЮЛ: ЕИО без блокировок · ЕГРИП: сам предприниматель",
     {"can": {"view": True, "prepare": True, "sign": True, "approve": False}}),
    ("Пользователь ДБО с подготовкой", "договор ДБО: уровень «подготовка» или «полный», не руководитель",
     {"can": {"view": True, "prepare": True, "sign": False, "approve": False}}),
    ("Представитель по МЧД", "реестр МЧД: действующая доверенность на кредитный договор + ДБО с подготовкой",
     {"can": {"view": True, "prepare": True, "sign": True, "approve": False}}),
    ("Наблюдатель", "договор ДБО: «просмотр»", {"can": {"view": True, "prepare": False, "sign": False, "approve": False}}),
    ("Участник ООО", "ЕГРЮЛ: доля в уставном капитале", {"can": {"view": True, "prepare": False, "sign": False, "approve": True},
                                                         "person_inn": P}),
    ("Кредитный специалист", "банк: решения по исключениям до порога", {"role": "loan_officer"}),
    ("Риск-менеджер", "банк: второй ключ выше порога", {"role": "risk_manager"}),
]


def _sample(status: str, pending: bool = False) -> dict:
    data = {"approval": {"status": "open", "method": "electronic", "participants": [{"inn": P}], "votes": []}} \
        if status == "INFO_REQUESTED" else {}
    if pending:
        data["pending_decision"] = {"by": "bank:other"}
    return {"status": status, "flags": [], "data": data}


def _cell(status: str, spec: dict) -> str:
    acts = lifecycle.actions(_sample(status), spec.get("can"), role=spec.get("role", "client"), person_inn=spec.get("person_inn"))
    if spec.get("role") == "risk_manager" and status == "UNDER_REVIEW":
        acts = list(dict.fromkeys(acts + lifecycle.actions(_sample(status, True), role="risk_manager")))
    return ", ".join(ACTIONS.get(a, a) for a in acts) or "—"


def _system(status: str) -> str:
    moves = [f"{'/'.join(KIND[k] for k in sorted(kinds) if k in KIND)} → {dst}" for (src, dst), kinds in EDGES.items()
             if src == status and kinds & set(KIND)]
    return "; ".join(moves) or "—"


def _section_roles(pol: dict) -> list[str]:
    limit = f"{pol['params']['specialist_authority_max']:,}".replace(",", " ")
    auto = f"{pol['params']['auto_authority_max']:,}".replace(",", " ")
    table = [
        ("Руководитель или ИП", "ЕГРЮЛ (ЕИО) / ЕГРИП", "подать, принять оферту, подписать, отозвать",
         "14-ФЗ ст. 40 п. 3; ГК ст. 53, 23"),
        ("Пользователь ДБО с подготовкой", "договор ДБО", "подать, ответить на запрос, принять оферту — без подписи",
         "договор ДБО"),
        ("Представитель по МЧД", "реестр МЧД (ФНС) + договор ДБО", "подписать кредитный договор, пока доверенность действует; "
         "отозвана, истекла или нет полномочия — подписи нет", "ГК ст. 185, 185.1 п. 4; 63-ФЗ ст. 17.2"),
        ("Наблюдатель", "договор ДБО", "смотреть компанию и заявки", "договор ДБО"),
        ("Участник ООО", "ЕГРЮЛ (доля)", "голосовать за крупную сделку: голос — по доле, нужно больше половины всех голосов",
         "14-ФЗ ст. 46 п. 3, ст. 32 п. 1, ст. 37 п. 7, ст. 38 п. 2"),
        ("Кредитный специалист", "банк", f"одобрить (в т. ч. другую сумму и срок по той же цене риска), отказать, "
         f"дозапросить — сам до {limit} ₽", "политика банка"),
        ("Риск-менеджер", "банк", f"подтвердить или вернуть одобрение специалиста выше {limit} ₽ (принцип четырёх глаз)",
         "политика банка"),
        ("Конвейер", "система", f"собрать данные, решить по правилам (сам — до {auto} ₽), выдать в АБС", "docs/04, docs/07"),
        ("Таймер", "система", "истекают оферта, подпись, дозапрос, черновик; просроченный SLA специалиста — флаг", "docs/04 §9"),
    ]
    return [
        "## 1. Кто есть кто",
        "",
        "Роли не назначаются вручную: клиентские считаются из ЕГРЮЛ/ЕГРИП и договора ДБО на каждый запрос "
        "(`app/domain/rights.py`, docs/05 §3), банковские — должность сотрудника. Один человек может быть в разных ролях "
        "в разных компаниях (Иванов: директор в «Северном Хлебе», участник с просмотром в «Склад-Логистик», "
        "подготовка в «Лента-Опт»).",
        "",
        "| Роль | Откуда | Что может | Основание |",
        "|---|---|---|---|",
        *[f"| {role} | {source} | {can} | {norm} |" for role, source, can, norm in table],
        "",
    ]


def _section_matrix() -> list[str]:
    head = "| Статус | " + " | ".join(name for name, _, _ in ROLES) + " | Система |"
    lines = ["## 2. Кто что может в каждом статусе", "",
             "Собрано из кода: те же правила отдают кнопки фронту (`available_actions` у заявки). Отозвать заявку можно "
             "до выдачи (ГК ст. 821 п. 2). Подпись недоступна, пока условия предварительные (нет кредитной истории).", "",
             head, "|---|" + "---|" * (len(ROLES) + 1)]
    for status in STATUSES:
        if status in TERMINAL:
            continue
        lines.append(f"| {status} | " + " | ".join(_cell(status, spec) for _, _, spec in ROLES) + f" | {_system(status)} |")
    lines += ["", f"Конец заявки — {', '.join(sorted(TERMINAL))}: действий нет, клиент начинает новую заявку.", ""]
    return lines


def _section_users() -> list[str]:
    pol = load()
    lines = ["## 3. Пользователи симулятора", "",
             "Вход — по ID, ИНН человека или ИНН компании (`POST /api/v1/auth/login {\"login\": \"s7\"}`) или карточкой "
             "(`GET /api/v1/sandbox/personas` → `POST …/{id}/login`), в ответе токен. Люди без отдельного сценария добавлены "
             "по их связям с компаниями мира.", "",
             "| id | Кто | Компания | Права | Сценарий |", "|---|---|---|---|---|"]
    for p in personas.presets():
        c = personas.card(p, "ru", limit=pol["params"]["specialist_authority_max"])
        lines.append(f"| `{c['id']}` | {c['full_name']} | {c['organization']} | {c['permissions']} | {c['scenario']} |")
    return lines + [""]


def _name(user: str, cards: dict) -> str:
    return "конвейер" if user == "system" else f"{cards[user]['full_name']} ({cards[user]['code']})"


def _section_flows() -> list[str]:
    cards = {p["id"]: personas.card(p, "ru") for p in personas.presets()}
    lines = ["## 4. Сценарии: как меняется статус между ролями", "",
             "Каждый сценарий прокликивается сквозным тестом `tests/e2e/test_flows.py` через HTTP API: шаг — от лица своего "
             "пользователя со своим токеном, после шага сверяется статус. «Пробует» — запрос уходит и получает 403.", ""]
    for i, flow in enumerate(FLOWS, 1):
        lines += [f"### 4.{i}. {flow.title}", "", flow.about, "", "| # | Кто | Действие | Статус после | Что происходит |",
                  "|---|---|---|---|---|"]
        for n, step in enumerate(flow.steps, 1):
            action = ACTION_TEXT[step.action] + (f" {ARG_TEXT.get(step.arg, step.arg)}" if step.arg is not None else "")
            lines.append(f"| {n} | {_name(step.user, cards)} | {action} | {step.status or '—'} | {step.note or '—'} |")
        lines.append("")
    return lines


def _section_flags() -> list[str]:
    cat = flags.catalog()
    lines = ["## 5. Своя компания: флаги, которые меняют решение", "",
             "Конструктор (`POST /api/v1/sandbox/personas`, поле `flags`; каталог — `GET /api/v1/sandbox/persona-options`) "
             "задаёт параметры компании поверх полей и включает отказы источников. Что каждый флаг действительно меняет решение "
             "на эталонной заявке, проверяет `tests/test_persona_flags.py`. Данные — `seed/persona_flags.yaml`.", "",
             "| Флаг | Группа | Формы | Что происходит |", "|---|---|---|---|"]
    for name, f in cat["flags"].items():
        lines.append(f"| `{name}` — {f['title']['ru']} | {cat['groups'][f['group']]['ru']} | {', '.join(f['forms'])} | "
                     f"{f['effect']['ru']} |")
    return lines + [""]


def render() -> str:
    pol = load()
    return "\n".join([
        "# 15. Роли и статусы",
        "",
        "Сгенерировано из кода: `cd backend && uv run python -m qa.roles`. Источник правды — `app/domain/rights.py`, "
        "`app/lifecycle.py`, `app/domain/state.py`, `seed/personas.yaml`, `seed/flows.py`, `seed/persona_flags.yaml`.",
        "",
        *_section_roles(pol),
        *_section_matrix(),
        *_section_users(),
        *_section_flows(),
        *_section_flags(),
    ])


def main() -> None:
    OUT.write_text(render(), "utf-8")
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
