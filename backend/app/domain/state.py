"""Статусы заявки и допустимые переходы (docs/diagrams/application_state.md). Диаграмма и проверки графа строятся отсюда."""

STATUSES = (
    "DRAFT", "SUBMITTED", "CHECKING", "INFO_REQUESTED", "UNDER_REVIEW", "OFFERED", "SIGNING", "SIGNED",
    "DISBURSING", "ISSUED", "REJECTED", "DECLINED", "WITHDRAWN", "EXPIRED",
)
TERMINAL = frozenset({"ISSUED", "REJECTED", "DECLINED", "WITHDRAWN", "EXPIRED"})
FLAGS = ("DEGRADED_DATA", "SOURCE_WAIT", "PROVISIONAL", "RECHECK", "SLA_BREACH", "DISBURSE_ERROR")

# Кто запускает переход: client — человек в кабинете, system — конвейер, timer — истёк срок, bank — кредитный специалист.
# Отозвать можно из любого статуса до DISBURSING; после подписи это отказ от получения (ГК ст. 821 п. 2).
EDGES: dict[tuple[str, str], frozenset[str]] = {
    ("DRAFT", "SUBMITTED"): frozenset({"client"}),
    ("DRAFT", "WITHDRAWN"): frozenset({"client", "timer"}),            # удалить или 30 дней без подачи
    ("SUBMITTED", "CHECKING"): frozenset({"system"}),
    ("SUBMITTED", "WITHDRAWN"): frozenset({"client"}),
    ("CHECKING", "OFFERED"): frozenset({"system"}),                    # APPROVE · COUNTER_OFFER · APPROVE_WITH_CONDITIONS
    ("CHECKING", "INFO_REQUESTED"): frozenset({"system"}),
    ("CHECKING", "UNDER_REVIEW"): frozenset({"system", "timer"}),      # MANUAL_REVIEW или источник не ответил до дедлайна
    ("CHECKING", "REJECTED"): frozenset({"system"}),
    ("CHECKING", "WITHDRAWN"): frozenset({"client"}),
    ("INFO_REQUESTED", "CHECKING"): frozenset({"client"}),             # ответ на системный дозапрос
    ("INFO_REQUESTED", "UNDER_REVIEW"): frozenset({"client"}),         # ответ на дозапрос специалиста
    ("INFO_REQUESTED", "EXPIRED"): frozenset({"timer"}),
    ("INFO_REQUESTED", "WITHDRAWN"): frozenset({"client"}),
    ("UNDER_REVIEW", "OFFERED"): frozenset({"bank"}),
    ("UNDER_REVIEW", "INFO_REQUESTED"): frozenset({"bank"}),
    ("UNDER_REVIEW", "REJECTED"): frozenset({"bank"}),
    ("UNDER_REVIEW", "WITHDRAWN"): frozenset({"client"}),
    ("OFFERED", "SIGNING"): frozenset({"client"}),
    ("OFFERED", "DECLINED"): frozenset({"client"}),
    ("OFFERED", "EXPIRED"): frozenset({"timer"}),
    ("OFFERED", "CHECKING"): frozenset({"system"}),                    # пересмотр: пришли новые данные (RECHECK)
    ("OFFERED", "WITHDRAWN"): frozenset({"client"}),
    ("SIGNING", "SIGNED"): frozenset({"client"}),                      # подписали все, кто должен
    ("SIGNING", "EXPIRED"): frozenset({"timer"}),
    ("SIGNING", "CHECKING"): frozenset({"system"}),
    ("SIGNING", "WITHDRAWN"): frozenset({"client"}),
    ("SIGNED", "DISBURSING"): frozenset({"system"}),                   # перепроверка по свежим данным пройдена
    ("SIGNED", "REJECTED"): frozenset({"system"}),                     # всплыл стоп-фактор, ГК ст. 821 п. 1
    ("SIGNED", "UNDER_REVIEW"): frozenset({"system", "timer"}),        # финальную проверку не провести до дедлайна (N6)
    ("SIGNED", "WITHDRAWN"): frozenset({"client"}),
    ("DISBURSING", "ISSUED"): frozenset({"system"}),                   # зачислено, сверка по ключу идемпотентности
    ("DISBURSING", "UNDER_REVIEW"): frozenset({"system", "timer"}),    # сбой АБС до дедлайна
}

TRANSITIONS: dict[str, frozenset[str]] = {
    src: frozenset(dst for (s, dst) in EDGES if s == src) for src in dict.fromkeys(s for s, _ in EDGES)
}

# Исход решения → статус (docs/04 §8)
OUTCOME_STATUS = {
    "APPROVE": "OFFERED", "COUNTER_OFFER": "OFFERED", "APPROVE_WITH_CONDITIONS": "OFFERED",
    "REQUEST_INFO": "INFO_REQUESTED", "MANUAL_REVIEW": "UNDER_REVIEW", "REJECT": "REJECTED",
}


class TransitionError(ValueError):
    pass


def can(src: str, dst: str) -> bool:
    return (src, dst) in EDGES


def check(src: str, dst: str) -> None:
    if not can(src, dst):
        raise TransitionError(f"переход {src} → {dst} запрещён")


def mermaid() -> str:
    lines = ["stateDiagram-v2", "    [*] --> DRAFT"]
    lines += [f"    {src} --> {dst}: {' / '.join(sorted(kinds))}" for (src, dst), kinds in EDGES.items()]
    lines += [f"    {s} --> [*]" for s in sorted(TERMINAL)]
    return "\n".join(lines)
