"""Вход персоной, права из реестров, главная, своя персона из конструктора фронта и предварительная оферта (N1)."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.anyio]

SMIRNOVA, HLEB, SKLAD, LENTA = "770100000079", "7701000040", "7701000058", "7701000065"
MSK = ZoneInfo("Europe/Moscow")


async def test_personas_list_matches_frontend_contract(stand):
    items = await stand.call("GET", "/sandbox/personas", params={"lang": "en"})
    fields = {"id", "badge", "role_title", "about", "code", "kind", "full_name", "organization", "scenario", "permissions",
              "profile", "registries", "preview", "login_label"}
    assert all(fields <= set(item) for item in items)
    ids = {i["id"] for i in items}
    assert ids >= {"s7", "s3", "s2", "s4", "bank", "u-kotov"} and not ids & {"n1", "n2", "r8"}   # без сценариев отказов и дублей
    assert next(i for i in items if i["id"] == "bank")["kind"] == "bank"
    ru = await stand.call("GET", "/sandbox/personas")
    assert not any(i["code"] in {"S7", "N1", "R12"} or "Что увидите" in i["preview"] for i in ru)        # не тест-кейсы
    assert next(i for i in ru if i["id"] == "s4")["registries"] == "Все источники отвечают"           # исход не подсказываем
    assert next(i for i in ru if i["id"] == "bank")["permissions"].endswith("до 15 млн ₽")           # полномочия из политики


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
        # счёт компании участник без доступа в ДБО не видит — только заявку, где банк просит его голос
        assert not me["companies"][0]["can"]["view"]
        denied = await stand.api.get(f"/companies/{owner['inn']}/insights", headers=member_headers)
        assert denied.status_code == 403 and denied.json()["code"] == "FORBIDDEN"
        summary = await stand.call("GET", f"/companies/{owner['inn']}/applications/summary", member_headers)
        assert [a["id"] for a in summary["applications"]] == [app["id"]]
        assert [t["action"] for t in summary["all_tasks"]] == ["vote"]
        visible = await stand.call("GET", path, member_headers)
        assert "vote" in visible["available_actions"] and "sign" not in visible["available_actions"]
        voted = await stand.call("POST", f"{path}/approvals/vote", member_headers, json={"vote": "for"})
    assert voted["status"] == "CHECKING"
    authors = {e["by"]["name"] for e in await stand.call("GET", f"{path}/events", owner_headers) if e["by"]["kind"] == "client"}
    assert "Олег Петров" in authors and len(authors) == 3                         # кто голосовал — по имени, не «вы»

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


async def test_builder_company_structure_drives_the_flow(stand):
    """Своя компания простыми ответами: два директора подписывают вместе (ГК ст. 53 п. 1), бухгалтер готовит, но не
    подписывает, доверенность одного представителя при совместных директорах не работает — путь заявки следует из устава."""
    options = await stand.call("GET", "/sandbox/persona-options")
    assert {"industries", "structures", "people", "choices"} <= set(options)
    assert next(s for s in options["structures"] if s["id"] == "two_directors_joint")["means"].endswith("(ГК ст. 53 п. 1)")
    conflict = await stand.api.post("/sandbox/personas", json={"structure": "owner_director", "flags": ["large_deal"]})
    assert conflict.status_code == 422 and conflict.json()["code"] == "STRUCTURE_CONFLICT"   # один владелец ≠ три участника
    jsc = await stand.api.post("/sandbox/personas", json={"form": "JSC", "structure": "partners"})
    assert jsc.status_code == 422 and jsc.json()["code"] == "STRUCTURE_NOT_APPLICABLE"       # акционеров нет в ЕГРЮЛ
    owner = await stand.call("POST", "/sandbox/personas", expect=201, json={
        "full_name": "Ольга Петрова", "organization": "Пекарня у дома", "industry": "bakery", "structure": "two_directors_joint",
        "accountant": True, "representative": True, "seasonality": "flat", "channel": "invoices", "loans": "none"})
    cards = [c for c in await stand.call("GET", "/sandbox/personas") if c["company_inn"] == owner["inn"]]
    by_badge = {c["badge"]: c for c in cards}
    assert owner["role_title"] == "Генеральный директор «Пекарня у дома», доля 60%" and len(cards) == 4
    assert {"Директор", "Бухгалтер", "Сотрудник"} <= set(by_badge)          # второй директор, бухгалтер, представитель
    second = next(c for c in cards if c["id"] != owner["id"] and c["badge"] == "Директор")

    accountant = await stand.login(by_badge["Бухгалтер"]["id"])
    app = await stand.call("POST", "/applications", accountant, expect=201,
                           json={"inn": owner["inn"], "product": "OVERDRAFT", "amount": 300000, "goal": "cash_gap",
                                 "consent_bki": True})
    path = f"/applications/{app['id']}"
    await stand.call("POST", f"{path}/submit", accountant)
    await stand.pump()
    offered = await stand.call("GET", path, accountant)
    assert offered["status"] == "OFFERED" and "accept_offer" in offered["available_actions"]
    await stand.call("POST", f"{path}/offer/accept", accountant)
    denied = await stand.api.post(f"{path}/signatures", headers=accountant)
    assert denied.status_code == 403                                         # бухгалтер не подписывает

    representative = await stand.login(by_badge["Сотрудник"]["id"])
    assert "sign" not in (await stand.call("GET", path, representative))["available_actions"]
    first = await stand.login(owner["id"])
    signed_once = await stand.call("POST", f"{path}/signatures", first)
    assert signed_once["status"] == "SIGNING" and signed_once["signers"]["mode"] == "joint"   # ждём второго директора
    assert "sign" not in signed_once["available_actions"]                    # кнопки у подписавшего больше нет
    both = await stand.call("POST", f"{path}/signatures", await stand.login(second["id"]))
    assert both["status"] == "SIGNED"
    await stand.pump()
    assert (await stand.call("GET", path, first))["status"] == "ISSUED"


async def test_issued_overdraft_changes_the_cabinet(stand):
    """Выданное не теряется: подключённый овердрафт прикрывает разрыв и второй раз не предлагается, выдача — по часам мира."""
    await stand.advance(24 * 3600)                         # выдача после перемотки: сброс вернёт часы назад, а кредит забудет
    headers = await stand.login("s7")
    before = await stand.call("GET", f"/companies/{SMIRNOVA}/insights", headers)
    assert before["cash_forecast"]["status"] == "CASH_GAP" and before["offer"]["product"] == "OVERDRAFT"
    cover = before["offer"]["cover"]
    assert cover["amount"] == before["cash_forecast"]["cash_gap"]["amount"] and 0 < cover["interest"] < 1000
    app = await stand.call("POST", "/applications", headers, expect=201,
                           json={"inn": SMIRNOVA, "product": "OVERDRAFT", "amount": before["offer"]["amount"],
                                 "goal": "cash_gap", "consent_bki": True})
    path = f"/applications/{app['id']}"
    await stand.call("POST", f"{path}/submit", headers)
    await stand.pump()
    await stand.call("POST", f"{path}/offer/accept", headers)
    await stand.call("POST", f"{path}/signatures", headers)
    await stand.pump()
    issued = await stand.call("GET", path, headers)
    assert issued["status"] == "ISSUED" and issued["loan"]["kind"] == "limit" and issued["loan"]["number"].startswith("КД-")
    today = (await stand.call("GET", "/sandbox/clock"))["today"]
    assert datetime.fromisoformat(issued["loan"]["disbursed_at"]).astimezone(MSK).date().isoformat() == today

    after = await stand.call("GET", f"/companies/{SMIRNOVA}/insights", headers)
    assert after["cash_forecast"]["status"] == "COVERED" and after["offer"] is None
    assert after["cash_forecast"]["credit_line"] == before["offer"]["amount"]
    assert "OVERDRAFT" not in {p["product"] for p in await stand.call("GET", f"/companies/{SMIRNOVA}/products", headers)}

    bank = await stand.login("bank")                       # банк видит и то, что движок решил сам, а не только очередь
    register = await stand.call("GET", "/bank/applications", bank, params={"q": "смирнова"})
    row = next(r for r in register if r["id"] == app["id"])
    assert row["decided_by"] == "engine" and row["status"] == "ISSUED" and row["loan"]["kind"] == "limit"
    assert not [r for r in await stand.call("GET", "/bank/applications", bank, params={"decided_by": "bank"})
                if r["id"] == app["id"]]
    assert (await stand.call("GET", f"/bank/applications/{app['id']}/dossier", bank))["application"]["id"] == app["id"]

    await stand.call("POST", "/sandbox/reset")             # мир как сначала: заявка в истории, кредит в прогнозе не учитывается
    headers = await stand.login("s7")
    again = await stand.call("GET", f"/companies/{SMIRNOVA}/insights", headers)
    assert again["cash_forecast"]["status"] == "CASH_GAP" and again["offer"]["product"] == "OVERDRAFT"
    assert (await stand.call("GET", path, headers))["status"] == "ISSUED"


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
