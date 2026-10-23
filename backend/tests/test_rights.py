"""Права из сущностей реестров и ДБО (docs/05 §2–3) — таблица случаев, которых нет в демо-мире целиком."""

import pytest

from app.domain.rights import rights, signed_enough, signers

A, B, C = "770000000001", "770000000002", "770000000003"


def company(**kw) -> dict:
    return {"inn": "7700000001", "segment": "LLC", "eio_mode": "independent", "eio": [], "participants": [], "bank_access": [],
            **kw}


def poa(inn: str, status: str = "ACTIVE", powers: tuple = ("CREDIT_AGREEMENT_SIGN",)) -> dict:
    return {"guid": f"poa-{inn}", "representative_inn": inn, "fio": "Представитель", "status": status, "powers": list(powers),
            "valid_to": "2027-06-30", "active": status == "ACTIVE"}


CASES = {
    "ИП сам себе руководитель": (company(inn=A, segment="IP"), A, {"view", "prepare", "sign"}),
    "директор без блокировок": (company(eio=[{"inn": A, "title": "Директор"}]), A, {"view", "prepare", "sign"}),
    "директор дисквалифицирован": (company(eio=[{"inn": A, "title": "Директор", "disqualified": True}]), A, {"view"}),
    "сведения о директоре недостоверны, но есть ДБО": (
        company(eio=[{"inn": A, "title": "Директор", "unreliable": True}], bank_access=[{"inn": A, "level": "prepare"}]),
        A, {"view", "prepare"}),
    # счёт компании видит тот, кому компания дала доступ по договору ДБО; участник — только своё голосование в заявке
    "участник ООО голосует, но счёт не видит и не подписывает": (company(participants=[{"inn": A, "share": 30.0}]), A,
                                                                 {"approve"}),
    "участник ООО с доступом в ДБО видит счёт и голосует": (
        company(participants=[{"inn": A, "share": 30.0}], bank_access=[{"inn": A, "level": "view"}]), A, {"view", "approve"}),
    "акционер АО в ЕГРЮЛ не виден — ни голоса, ни счёта": (
        company(segment="JSC", participants=[{"inn": A, "share": 30.0}]), A, set()),
    "ДБО только просмотр": (company(bank_access=[{"inn": A, "level": "view"}]), A, {"view"}),
    "чужой человек": (company(eio=[{"inn": B, "title": "Директор"}]), A, set()),
    "представитель по действующей МЧД подписывает": (
        company(eio=[{"inn": B, "title": "Директор"}], poa=[poa(A)], bank_access=[{"inn": A, "level": "prepare"}]),
        A, {"view", "prepare", "sign"}),
    "МЧД отозвана — подписи нет": (company(eio=[{"inn": B, "title": "Директор"}], poa=[poa(A, status="REVOKED")]), A, {"view"}),
    "в МЧД нет полномочия на кредитный договор": (company(poa=[poa(A, powers=["TAX_REPORTING"])]), A, {"view"}),
    "совместные директора — доверенности одного мало": (
        company(eio_mode="joint", eio=[{"inn": B, "title": "Директор"}, {"inn": C, "title": "Директор"}], poa=[poa(A)]),
        A, {"view"}),
}


@pytest.mark.parametrize("name", list(CASES))
def test_rights_follow_registry_roles(name):
    facts, person, expected = CASES[name]
    granted = rights(person, facts)
    assert {k for k, v in granted["can"].items() if v} == expected
    assert all(w["norm"] for w in granted["why"])                       # у каждого «можно / нельзя» есть основание


def test_joint_directors_sign_together_and_blocked_one_is_skipped():
    joint = company(eio_mode="joint", eio=[{"inn": A, "title": "Директор"}, {"inn": B, "title": "Директор"},
                                           {"inn": C, "title": "Директор", "disqualified": True}])
    assert signers(joint) == {"mode": "joint", "required": [A, B], "any_of": []}
    assert not signed_enough(joint, {A}) and signed_enough(joint, {A, B})
    independent = company(eio=[{"inn": A, "title": "Директор"}, {"inn": B, "title": "Директор"}])
    assert signed_enough(independent, {B})
    assert not signed_enough(company(eio=[{"inn": A, "title": "Директор", "unreliable": True}]), {A})


def test_representative_by_poa_completes_signing_of_an_independent_director():
    facts = company(eio=[{"inn": B, "title": "Директор"}], poa=[poa(A)])
    assert set(signers(facts)["any_of"]) == {A, B} and signed_enough(facts, {A})
    assert rights(A, facts)["sign_mode"] == "poa"
    revoked = company(eio=[{"inn": B, "title": "Директор"}], poa=[poa(A, status="REVOKED")])
    assert signers(revoked)["any_of"] == [B] and not signed_enough(revoked, {A})
    assert "отозвана" in next(w["because"] for w in rights(A, revoked)["why"] if w["right"] == "sign")
