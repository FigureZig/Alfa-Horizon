"""Модель данных в docs/diagrams/data_model.md собрана из миграций и схем API (qa/er.py) и не отстаёт от них."""

from qa import er


def test_data_model_diagram_matches_migrations_and_schemas():
    assert er.OUT.read_text("utf-8") == er.render(), "перегенерируйте: uv run python -m qa.er"


def test_physical_model_has_every_table_and_link():
    names = {t["name"] for t in er.tables()}
    assert names == {"applications", "events", "jobs", "snapshots", "kv"}
    links = {(t["name"], c["fk"][0]) for t in er.tables() for c in t["columns"] if c["fk"]}
    assert links == {("events", "applications"), ("jobs", "applications")}
