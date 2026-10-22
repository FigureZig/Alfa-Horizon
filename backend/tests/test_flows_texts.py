"""Гид по сценариям двуязычный: у каждого сценария и каждой заметки шага есть английский текст (seed/flows.py EN)."""

from seed.flows import ACTION_TEXT, ACTION_TEXT_EN, ARG_TEXT, ARG_TEXT_EN, EN, FLOWS


def test_english_guide_covers_every_flow_and_note():
    assert set(EN) == {f.id for f in FLOWS}
    for flow in FLOWS:
        en = EN[flow.id]
        assert en["title"] and en["about"], flow.id
        for n, step in enumerate(flow.steps, 1):
            assert bool(step.note) == bool(en["notes"].get(n)), (flow.id, n, step.note)
    assert set(ACTION_TEXT_EN) == set(ACTION_TEXT) and set(ARG_TEXT_EN) >= set(ARG_TEXT)
