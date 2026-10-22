"""Демо-мир и сущности: идентификаторы с контрольными цифрами, согласованность источников, моки = мир."""

import copy
import filecmp
import json
import re
from decimal import Decimal
from pathlib import Path

import pytest

from app.api.sandbox import persona_stubs
from app.policy import sources as source_config
from app.sources import render
from seed import gen_mocks, world

from .conftest import COMPANIES, PEOPLE, TODAY, WORLD, mock_payloads

MOCKS = Path(__file__).resolve().parents[1] / "wiremock"


def test_identifier_checksums():
    assert world.inn_valid("7707083893") and not world.inn_valid("7707083894")     # ИНН юрлица: 10 цифр
    assert world.inn_valid("500100732259") and not world.inn_valid("500100732258")  # ИНН физлица: 12 цифр
    assert world.ogrn_valid("1027700132195") and not world.ogrn_valid("1027700132194")
    assert world.ogrn_valid(world.ogrn(2022, "77", 1, ip=True))
    assert world.snils("112233445") == "11223344595"


def test_demo_world_is_valid():
    assert {c["key"]: world.validate(c, PEOPLE, TODAY) for c in WORLD["companies"]} == {c["key"]: [] for c in WORLD["companies"]}


def test_derived_fields_agree_across_sources():
    """МСП и платежи не задаются руками: категория — из численности и дохода, платёж в выписке = платёж в БКИ."""
    romashka = mock_payloads("7701000033")
    assert romashka["rsmp"]["Документ"]["@КатСубМСП"] == "2"                         # 30 человек — малое (209-ФЗ ст. 4)
    for inn in COMPANIES:
        p = mock_payloads(inn)
        report = p["bki"].get("CreditReportOfLegalPerson") or p["bki"]["CreditReportOfNaturalPerson"]
        in_bki = sum(float(k["AvgMonthPaymentSum"]) for k in report["Credits"]["Credit"])
        in_bank = {float(t["amount"]) for t in p["bank_tx"]["items"] if t["category"] == "loan_payment"}
        assert in_bank == ({round(in_bki, 2)} if in_bki else set()), inn


BROKEN = {
    "контрольная цифра ИНН": lambda c: c.update(inn=c["inn"][:-1] + str((int(c["inn"][-1]) + 1) % 10)),
    "год регистрации ≠ ОГРН": lambda c: c.update(registered="2015-01-10"),
    "доли участников ≠ 100%": lambda c: c.update(participants=[[c["participants"][0][0], 90]]),
    "регистрация в будущем": lambda c: c.update(registered="2027-01-01"),
    "11 месяцев поступлений": lambda c: c.update(inflows=c["inflows"][:11]),
    "неизвестный флаг": lambda c: c.update(flags=["sanctions"]),
    "кредит оплачен дольше срока": lambda c: c["bki"].update(credits=[[1_000_000, 20, 12, 12, 0]]),
    "не МСП по численности": lambda c: c.update(headcount=300),
}


@pytest.mark.parametrize("what", list(BROKEN))
def test_validate_catches_broken_description(what):
    company = copy.deepcopy(COMPANIES["7701000019"])
    BROKEN[what](company)
    assert world.validate(company, PEOPLE, TODAY), what


def test_sole_trader_cannot_have_legal_entity_marks():
    trader = copy.deepcopy(COMPANIES["770100000079"])
    trader["flags"] = ["unreliable_eio"]
    assert world.validate(trader, PEOPLE, TODAY)


def test_mocks_on_disk_match_the_world(tmp_path):
    """wiremock/ сгенерирован из текущих personas.yaml и world.py: правка без перегенерации не пройдёт."""
    gen_mocks.main(tmp_path)
    cmp = filecmp.dircmp(tmp_path, MOCKS)
    stack, diff = [cmp], []
    while stack:
        d = stack.pop()
        diff += d.left_only + d.right_only + filecmp.cmpfiles(d.left, d.right, d.common_files, shallow=False)[1]
        stack += d.subdirs.values()
    assert not diff, f"перегенерируйте моки: uv run python -m seed.gen_mocks ({diff[:5]})"


def test_every_stub_finds_its_body_file():
    for mapping_file in (MOCKS / "mappings").glob("*.json"):
        for stub in json.loads(mapping_file.read_text("utf-8"))["mappings"]:
            body = stub["response"].get("bodyFileName")
            if not body:
                continue
            folder = body.split("/{{")[0]
            keys = re.search(r"\(([\d|]+)\)", json.dumps(stub["request"])).group(1).split("|")
            missing = [k for k in keys if not (MOCKS / "__files" / folder / f"{k}.json").exists()]
            assert not missing, (stub["name"], missing)


def _hits(stub: dict, method: str, path: str, query: dict, body: dict) -> bool:
    r = stub["request"]
    return (r["method"] == method and r.get("urlPath") == path
            and all(query.get(k) == c["equalTo"] for k, c in r.get("queryParameters", {}).items())
            and all(body.get("subject", {}).get("inn") == p["matchesJsonPath"]["equalTo"] for p in r.get("bodyPatterns", [])))


@pytest.mark.parametrize("kind", ["IP", "LLC", "JSC"])
def test_custom_persona_answers_every_request_of_the_worker(kind):
    """Своя персона из песочницы: на каждый запрос worker (пути — policy/sources.yaml) ровно один стаб с её ответом."""
    company, people = world.custom({"kind": kind, "participants": 2, "contract_price": 5_000_000}, 77, TODAY)
    stubs, served = persona_stubs(company, people, TODAY), world.served(company, people, TODAY)
    for name, src in source_config()["sources"].items():
        if name not in served:
            continue
        path, _, query = render(src["path"], company["inn"]).partition("?")
        hits = [s for s in stubs if _hits(s, src["method"], path, dict([query.split("=")]) if query else {},
                                          render(src.get("body", {}), company["inn"]))]
        assert [h["response"]["jsonBody"] for h in hits] == [served[name]], name


@pytest.mark.parametrize("company", [*COMPANIES.values(), world.custom({"kind": "IP", "inflow_cv": 0.9}, 41, TODAY)[0],
                                     world.custom({"kind": "LLC", "debt_load": 0.6, "inflow_trend": -0.5}, 42, TODAY)[0]],
                         ids=lambda c: c["key"])
def test_statement_adds_up_and_never_goes_negative(company):
    """Выписка как у настоящего счёта: входящий + обороты = сегодняшний, остаток не уходит в минус, счёт с верным ключом."""
    tx = world.transactions(company, TODAY)
    running = Decimal(tx["openingBalance"]["amount"])
    for t in tx["items"]:
        running += Decimal(t["amount"]) if t["direction"] == "in" else -Decimal(t["amount"])
        assert Decimal(t["balanceAfter"]) == running >= 0, t
    assert running == Decimal(tx["balance"]["amount"])
    assert world.account_valid(tx["account"]) and tx["account"][:5] == ("40702" if world.is_ul(company) else "40802")
