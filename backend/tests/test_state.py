import pytest

from app.domain import state


@pytest.mark.parametrize("src,dst", [("DRAFT", "SUBMITTED"), ("CHECKING", "OFFERED"), ("OFFERED", "CHECKING"),
                                     ("SIGNED", "REJECTED"), ("SIGNED", "WITHDRAWN"), ("DISBURSING", "ISSUED")])
def test_allowed(src, dst):
    state.check(src, dst)


@pytest.mark.parametrize("src,dst", [("DRAFT", "OFFERED"), ("ISSUED", "CHECKING"), ("DISBURSING", "WITHDRAWN"),
                                     ("REJECTED", "OFFERED")])
def test_forbidden(src, dst):
    with pytest.raises(state.TransitionError):
        state.check(src, dst)


def test_terminal_states_have_no_exits():
    assert all(s not in state.TRANSITIONS for s in state.TERMINAL)


def test_every_outcome_maps_to_reachable_status():
    assert all(state.can("CHECKING", st) for st in state.OUTCOME_STATUS.values())


def test_diagram_is_generated_from_table():
    assert "CHECKING --> OFFERED" in state.mermaid()
