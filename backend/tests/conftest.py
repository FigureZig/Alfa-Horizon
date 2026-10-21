"""Тесты домена без БД и сети: факты собираем прямо из сгенерированных моков (wiremock/__files)."""

import json
from datetime import date
from pathlib import Path

import pytest
import yaml

from app.features import company_facts
from app.policy import load

ROOT = Path(__file__).resolve().parents[1]
WORLD = yaml.safe_load((ROOT / "seed" / "personas.yaml").read_text("utf-8"))
TODAY = date.fromisoformat(WORLD["today"])
FILES = ROOT / "wiremock" / "__files"
SOURCE_FOLDERS = {
    "egrul": "egrul", "egrip": "egrip", "rsmp": "fns/rsmp", "sshr": "fns/sshr", "paytax": "fns/paytax",
    "debtam": "fns/debtam", "snr": "fns/snr", "girbo": "girbo/bfo", "legal": "legal", "bank_access": "bank/access",
    "bank_charter": "bank/charter", "bank_tx": "bank/tx", "eis": "eis", "bki": "bki", "bki_info": "bki-info",
}


def mock_payloads(inn: str, without: tuple[str, ...] = ()) -> dict:
    out = {}
    for source, folder in SOURCE_FOLDERS.items():
        path = FILES / folder / f"{inn}.json"
        if source not in without and path.exists():
            out[source] = json.loads(path.read_text("utf-8"))
    return out


def facts_of(inn: str, without: tuple[str, ...] = ()) -> dict:
    return company_facts(inn, mock_payloads(inn, without), TODAY)


@pytest.fixture(scope="session")
def pol() -> dict:
    return load()
