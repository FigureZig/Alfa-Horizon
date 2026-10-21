"""Тесты домена без БД и сети: ответы источников строим в памяти тем же seed/world.py, что пишет моки WireMock,
и пропускаем через JSON — движок видит ровно то, что отдал бы WireMock."""

from datetime import date
from functools import cache

import pytest

from app.features import company_facts
from app.policy import load
from seed import world

WORLD = world.load()
TODAY = date.fromisoformat(WORLD["today"])
PEOPLE = WORLD["people"]
COMPANIES = {c["inn"]: c for c in WORLD["companies"]}


@cache
def _served(inn: str) -> dict:
    return world.served(COMPANIES[inn], PEOPLE, TODAY)


def mock_payloads(inn: str, without: tuple[str, ...] = ()) -> dict:
    return {source: body for source, body in _served(inn).items() if source not in without}


def facts_of(inn: str, without: tuple[str, ...] = ()) -> dict:
    return company_facts(inn, mock_payloads(inn, without), TODAY)


@pytest.fixture(scope="session")
def pol() -> dict:
    return load()
