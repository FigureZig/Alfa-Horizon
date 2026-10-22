"""Вход персоной, права из реестров, главная, своя персона из конструктора фронта и предварительная оферта (N1)."""

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.anyio]

SMIRNOVA, HLEB, SKLAD, LENTA = "770100000079", "7701000040", "7701000058", "7701000065"


async def test_personas_list_matches_frontend_contract(stand):
    items = await stand.call("GET", "/sandbox/personas", params={"lang": "en"})
    fields = {"id", "code", "kind", "full_name", "organization", "scenario", "permissions", "profile", "registries",
              "preview", "login_label"}
    assert all(fields <= set(item) for item in items)
    assert {i["id"] for i in items} >= {"s7", "s3", "s2", "s4", "r8", "n1", "bank"}
    assert next(i for i in items if i["id"] == "bank")["kind"] == "bank"


async def test_one_person_three_companies_different_rights(stand):
    headers = await stand.login("r8")
    me = await stand.call("GET", "/me", headers)
    can = {c["inn"]: c["can"] for c in me["companies"]}
    assert not me["loading"] and set(can) == {HLEB, SKLAD, LENTA}
    assert can[HLEB] == {"view": True, "prepare": True, "sign": True, "approve": True}       # ЕИО и участник 60%
    assert can[SKLAD] == {"view": True, "prepare": False, "sign": False, "approve": True}    # участник 40%, ДБО — просмотр
    assert can[LENTA] == {"view": True, "prepare": True, "sign": False, "approve": False}    # ДБО — подготовка
    denied = await stand.api.post("/applications", headers=headers,
                                  json={"inn": SKLAD, "product": "OVERDRAFT", "amount": 500000, "goal": "cash_gap"})
    assert denied.status_code == 403 and denied.json()["code"] == "FORBIDDEN"
    assert denied.headers["content-type"].startswith("application/problem+json")


async def test_dashboard_and_quick_offer(stand):
    headers = await stand.login("s7")
    board = await stand.call("GET", "/dashboard", headers)
    assert board["company"]["inn"] == SMIRNOVA
    assert board["total_balance"] == "330000.00" and len(board["cash_flow"]) == 6
    assert board["offer"]["product"] == "OVERDRAFT" and board["offer"]["label"] == "PREAPPROVED"
    assert board["recent_transactions"][0]["date"] <= "2026-10-21"


async def test_custom_persona_from_frontend_builder(stand):
    payload = {"kind": "client", "full_name": "Анна Петрова", "organization": "ООО «Ромашка»", "code": "MY",
               "scenario": "Своя кофейня", "permissions": "", "profile": "", "registries": "", "preview": "Подбор",
               "login_label": "Войти как Анна"}
    card = await stand.call("POST", "/sandbox/personas", json=payload, expect=201)
    assert card["full_name"] == "Анна Петрова" and card["organization"] == "ООО «Ромашка»"
    assert card["permissions"].startswith("Генеральный директор")                         # пустые тексты считает бэкенд
    headers = await stand.login(card["id"])
    me = await stand.call("GET", "/me", headers)
    assert [c["name"] for c in me["companies"]] == ["ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ «Ромашка»"]
    products = await stand.call("GET", f"/companies/{me['companies'][0]['inn']}/products", headers,
                                params={"goal": "cash_gap", "amount": 500000})
    assert {p["product"] for p in products} == {"OVERDRAFT", "EXPRESS"}


async def test_custom_company_members_can_approve_a_large_deal(stand):
    owner = await stand.call("POST", "/sandbox/personas", expect=201,
                             json={"full_name": "Олег Петров", "organization": "ООО «Пекарня»",
                                   "participants": 3, "flags": ["large_deal"]})
    cards = await stand.call("GET", "/sandbox/personas")
    members = [card for card in cards if card["company_inn"] == owner["inn"]]
    assert len(members) == 3
    assert len({card["id"] for card in members}) == len({card["person_inn"] for card in members}) == 3
    assert members[0]["id"] == owner["id"]
    assert all(card["custom"] and card["kind"] == "client" for card in members)
    assert all("Участник" in card["scenario"] for card in members[1:])

    owner_headers = await stand.login(owner["id"])
    app = await stand.call("POST", "/applications", owner_headers, expect=201,
                           json={"inn": owner["inn"], "product": "EXPRESS", "amount": 1_500_000,
                                 "term_months": 24, "goal": "growth", "consent_bki": True})
    path = f"/applications/{app['id']}"
    await stand.call("POST", f"{path}/submit", owner_headers)
    await stand.pump()
    waiting = await stand.call("GET", path, owner_headers)
    assert waiting["status"] == "INFO_REQUESTED"
    assert len(waiting["approval"]["participants"]) == 3

    for member in members[1:]:
        member_headers = await stand.login(member["id"])
        me = await stand.call("GET", "/me", member_headers)
        assert me["companies"][0]["can"]["approve"] and not me["companies"][0]["can"]["prepare"]
        visible = await stand.call("GET", path, member_headers)
        assert "vote" in visible["available_actions"] and "sign" not in visible["available_actions"]
        voted = await stand.call("POST", f"{path}/approvals/vote", member_headers, json={"vote": "for"})
    assert voted["status"] == "CHECKING"

    await stand.pump()
    offered = await stand.call("GET", path, owner_headers)
    assert offered["status"] == "OFFERED"
    if "PROVISIONAL" in offered["flags"]:
        await stand.advance(1)
        await stand.step(fast_forward=True)
        offered = await stand.call("GET", path, owner_headers)
        assert "PROVISIONAL" not in offered["flags"]
    await stand.call("POST", f"{path}/offer/accept", owner_headers, json={"variant": 0})
    await stand.call("POST", f"{path}/signatures", owner_headers)
    await stand.pump()
    assert (await stand.call("GET", path, owner_headers))["status"] == "ISSUED"


async def test_provisional_offer_signs_only_after_credit_history(stand):
    """N1: БКИ не отвечает → предварительная оферта; подпись заблокирована; БКИ вернулось → флаг снят → выдача."""
    headers = await stand.login("n1")
    app = await stand.call("POST", "/applications", headers, json={"inn": SMIRNOVA, "product": "OVERDRAFT", "amount": 400000,
                                                                   "goal": "cash_gap", "consent_bki": True}, expect=201)
    await stand.call("POST", f"/applications/{app['id']}/submit", headers)
    await stand.pump()
    offered = await stand.call("GET", f"/applications/{app['id']}", headers)
    assert offered["status"] == "OFFERED" and "PROVISIONAL" in offered["flags"]
    await stand.call("POST", f"/applications/{app['id']}/offer/accept", headers)
    blocked = await stand.api.post(f"/applications/{app['id']}/signatures", headers=headers)
    assert blocked.status_code == 409 and blocked.json()["code"] == "BKI_PENDING"

    for fault in await stand.call("GET", "/sandbox/faults"):                            # БКИ вернулось
        await stand.call("DELETE", f"/sandbox/faults/{fault['id']}")
    await stand.advance(1)                                                              # sweeper ставит догоняющую проверку
    await stand.step(fast_forward=True)
    confirmed = await stand.call("GET", f"/applications/{app['id']}", headers)
    assert "PROVISIONAL" not in confirmed["flags"] and "sign" in confirmed["available_actions"]
    await stand.call("POST", f"/applications/{app['id']}/signatures", headers)
    await stand.pump()
    assert (await stand.call("GET", f"/applications/{app['id']}", headers))["status"] == "ISSUED"


async def test_tokenless_requests_act_as_active_persona(stand):
    await stand.login("bank")
    queue = await stand.api.get("/bank/queue")
    assert queue.status_code == 200 and queue.json() == {"data": []}
    forged = await stand.api.get("/me", headers={"Authorization": "Bearer not.a.token"})
    assert forged.status_code == 401 and forged.json()["code"] == "TOKEN_INVALID"
