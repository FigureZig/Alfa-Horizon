"""Жизненный цикл заявки: таблица переходов и её свойства как графа (qa/graph.py)."""

import re
from pathlib import Path

import pytest

from app.domain import state
from qa import graph


@pytest.mark.parametrize("src,dst", [("DRAFT", "SUBMITTED"), ("CHECKING", "OFFERED"), ("OFFERED", "CHECKING"),
                                     ("SIGNED", "REJECTED"), ("SIGNED", "WITHDRAWN"), ("DISBURSING", "ISSUED")])
def test_allowed(src, dst):
    state.check(src, dst)


@pytest.mark.parametrize("src,dst", [("DRAFT", "OFFERED"), ("ISSUED", "CHECKING"), ("DISBURSING", "WITHDRAWN"),
                                     ("REJECTED", "OFFERED")])
def test_forbidden(src, dst):
    with pytest.raises(state.TransitionError):
        state.check(src, dst)


def test_every_outcome_maps_to_reachable_status():
    assert all(state.can("CHECKING", st) for st in state.OUTCOME_STATUS.values())


def test_diagram_is_generated_from_table():
    assert "CHECKING --> OFFERED: system" in state.mermaid()


def test_status_diagram_in_docs_matches_the_table():
    doc = Path(__file__).resolve().parents[2] / "docs" / "diagrams" / "application_state.md"
    if not doc.exists():
        pytest.skip("docs/ нет рядом (например, внутри образа)")
    text = doc.read_text("utf-8").split("## 2.")[0]
    drawn = {(a, b) for a, b in re.findall(r"^\s*(\w+)\s*-->\s*(\w+)", text, flags=re.M)
             if a in state.STATUSES and b in state.STATUSES}
    assert drawn == set(state.EDGES)


def test_graph_has_no_deadlocks_or_livelocks():
    g = graph.status_graph()
    assert graph.unreachable(g) == set()          # в каждый статус можно попасть из черновика
    assert graph.dead_ends(g) == set()            # из каждого нетерминального статуса можно завершиться
    assert graph.terminal_exits(g) == set()       # терминал — это конец
    assert graph.closed_cycles(g) == []           # нет круга, из которого не выйти


def test_application_never_hangs_without_a_deadline():
    """Заявка никогда не зависает (docs/07 §1): из каждого статуса есть выход по таймеру или конвейеру.
    Исключение — ожидание специалиста банка, его срок держит SLA."""
    assert graph.can_hang(graph.status_graph()) == graph.WAITS_FOR_BANK


def test_every_transition_has_a_trigger_and_a_way_to_cause_it_in_demo():
    assert all(kinds and kinds <= {"client", "system", "timer", "bank"} for kinds in state.EDGES.values())
    assert set(graph.HOW) == set(state.EDGES)


def test_covering_routes_pass_every_transition_with_fewest_runs():
    g = graph.status_graph()
    routes = graph.covering_routes(g)
    assert graph.uncovered(g, routes) == set()
    assert all(r[0] == "DRAFT" and r[-1] in state.TERMINAL for r in routes)
    assert all(state.can(a, b) for r in routes for a, b in zip(r, r[1:], strict=False))
    # каждый прогон кончается одним переходом в терминал — меньше прогонов не бывает
    assert len(routes) == sum(1 for _, dst in state.EDGES if dst in state.TERMINAL)
