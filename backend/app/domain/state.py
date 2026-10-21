"""Статусы заявки и допустимые переходы (docs/diagrams/application_state.md). Диаграмма генерируется отсюда."""

STATUSES = (
    "DRAFT", "SUBMITTED", "CHECKING", "INFO_REQUESTED", "UNDER_REVIEW", "OFFERED", "SIGNING", "SIGNED",
    "DISBURSING", "ISSUED", "REJECTED", "DECLINED", "WITHDRAWN", "EXPIRED",
)
TERMINAL = frozenset({"ISSUED", "REJECTED", "DECLINED", "WITHDRAWN", "EXPIRED"})
FLAGS = ("DEGRADED_DATA", "SOURCE_WAIT", "PROVISIONAL", "RECHECK", "SLA_BREACH", "DISBURSE_ERROR")

# Отозвать можно из любого статуса до DISBURSING; после подписи это отказ от получения (ГК ст. 821 п. 2).
TRANSITIONS: dict[str, frozenset[str]] = {
    "DRAFT": frozenset({"SUBMITTED", "WITHDRAWN"}),
    "SUBMITTED": frozenset({"CHECKING", "WITHDRAWN"}),
    "CHECKING": frozenset({"OFFERED", "INFO_REQUESTED", "UNDER_REVIEW", "REJECTED", "WITHDRAWN"}),
    "INFO_REQUESTED": frozenset({"CHECKING", "UNDER_REVIEW", "EXPIRED", "WITHDRAWN"}),
    "UNDER_REVIEW": frozenset({"OFFERED", "INFO_REQUESTED", "REJECTED", "WITHDRAWN"}),
    "OFFERED": frozenset({"SIGNING", "DECLINED", "EXPIRED", "CHECKING", "WITHDRAWN"}),
    "SIGNING": frozenset({"SIGNED", "EXPIRED", "CHECKING", "WITHDRAWN"}),
    "SIGNED": frozenset({"DISBURSING", "REJECTED", "WITHDRAWN"}),   # перепроверка перед выдачей, ГК ст. 821 п. 1
    "DISBURSING": frozenset({"ISSUED", "UNDER_REVIEW"}),
}

# Исход решения → статус (docs/04 §8)
OUTCOME_STATUS = {
    "APPROVE": "OFFERED", "COUNTER_OFFER": "OFFERED", "APPROVE_WITH_CONDITIONS": "OFFERED",
    "REQUEST_INFO": "INFO_REQUESTED", "MANUAL_REVIEW": "UNDER_REVIEW", "REJECT": "REJECTED",
}


class TransitionError(ValueError):
    pass


def can(src: str, dst: str) -> bool:
    return dst in TRANSITIONS.get(src, frozenset())


def check(src: str, dst: str) -> None:
    if not can(src, dst):
        raise TransitionError(f"переход {src} → {dst} запрещён")


def mermaid() -> str:
    lines = ["stateDiagram-v2", "    [*] --> DRAFT"]
    lines += [f"    {src} --> {dst}" for src, dsts in TRANSITIONS.items() for dst in sorted(dsts)]
    lines += [f"    {s} --> [*]" for s in sorted(TERMINAL)]
    return "\n".join(lines)
