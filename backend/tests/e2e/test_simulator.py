"""Вход по ID, рабочее место специалиста по ИНН банка, своя компания с флагами, честные тексты скоринга и ошибки статуса."""

import pytest

from seed import world

pytestmark = [pytest.mark.e2e, pytest.mark.anyio]

SMIRNOVA, BANK, HLEB = "770100000079", "7701000097", "7701000040"


async def test_login_by_id_inn_or_company_and_logout(stand):
    for login, user in (("S7", "s7"), ("r12", "r12"), ("770100001410", "u-novikova"), ("7701000065", "r12")):
        data = await stand.call("POST", "/auth/login", json={"login": login}, params={"wait_s": 0})
        assert data["persona"]["id"] == user and data["token"], login
    missing = await stand.api.post("/auth/login", json={"login": "nobody"})
    assert missing.status_code == 404 and missing.json()["code"] == "USER_NOT_FOUND"
    assert (await stand.call("POST", "/auth/logout"))["status"] == "ok"


async def test_wrong_status_is_409_with_application_status(stand):
    headers = await stand.login("s7")
    app = await stand.call("POST", "/applications", headers, expect=201,
                           json={"inn": SMIRNOVA, "product": "OVERDRAFT", "amount": 400000, "goal": "cash_gap"})
    resp = await stand.api.post(f"/applications/{app['id']}/offer/accept", headers=headers, json={"variant": 0})
    body = resp.json()
    assert resp.status_code == 409 and body["status"] == 409
    assert body["code"] == "INVALID_STATUS" and body["app_status"] == "DRAFT"


async def test_officer_opens_the_bank_workspace_by_bank_inn(stand):
    await stand.login("bank")
    cards = await stand.call("GET", f"/demo-personas/{BANK}/dashboard/summary")
    assert [c["type"] for c in cards] == ["balance", "outflow", "inflow"] and all(isinstance(c["amount"], float) for c in cards)
    assert (await stand.call("GET", f"/companies/{BANK}/insights"))["cash_forecast"] is None
    assert await stand.call("GET", f"/companies/{BANK}/products") == []
    assert (await stand.call("GET", f"/companies/{BANK}/profile"))["legal_form"] == "JSC"
    summary = await stand.call("GET", f"/companies/{BANK}/applications/summary")
    assert summary["tasks"] == [] and isinstance(summary["applications"], list)
    client = await stand.login("s7")
    denied = await stand.api.get(f"/companies/{BANK}/applications/summary", headers=client)
    assert denied.status_code == 403 and denied.json()["code"] == "BANK_ONLY"


async def test_pause_holds_applications_while_company_data_still_loads(stand):
    """Пауза — наш сбой: поданная заявка ждёт в очереди, а кабинет компании, в которую ещё не входили, открывается."""
    headers = await stand.login("s7")
    await stand.call("POST", "/sandbox/worker/pause")
    app = await stand.call("POST", "/applications", headers, expect=201,
                           json={"inn": SMIRNOVA, "product": "OVERDRAFT", "amount": 400000, "goal": "cash_gap"})
    await stand.call("POST", f"/applications/{app['id']}/submit", headers)
    assert await stand.call("GET", f"/companies/{HLEB}/profile", await stand.login("s5"))
    assert await stand.status(app["id"]) == "SUBMITTED"
    await stand.call("POST", "/sandbox/worker/resume")
    await stand.until_left(app["id"], "SUBMITTED")


async def test_custom_company_flags_change_the_outcome(stand):
    options = await stand.call("GET", "/sandbox/persona-options", params={"lang": "ru"})
    assert {"tax_debt", "large_deal", "bki_down"} <= {f["id"] for f in options["flags"]}
    assert {p["id"] for p in options["params"]} >= {"form", "inflow_avg", "debt_load"}
    card = await stand.call("POST", "/sandbox/personas", expect=201,
                            json={"full_name": "Олег Петров", "organization": "ООО «Пекарня»", "okved": "10.71",
                                  "flags": ["tax_debt", "bki_down"]})
    assert card["role_title"] == "Генеральный директор «Пекарня», доля 100%" and card["faults"]
    assert "недоимк" not in " ".join(str(v) for v in card.values()).lower()   # особенности компании решение покажет само
    headers = await stand.login(card["id"])
    app = await stand.call("POST", "/applications", headers, expect=201,
                           json={"inn": card["inn"], "product": "EXPRESS", "amount": 1000000, "term_months": 24,
                                 "goal": "growth"})
    await stand.call("POST", f"/applications/{app['id']}/submit", headers)
    await stand.pump()
    decided = await stand.call("GET", f"/applications/{app['id']}", headers)
    assert decided["status"] == "REJECTED" and "STOP_TAX_DEBT" in {r["code"] for r in decided["decision"]["reasons"]}
    wrong = await stand.api.post("/sandbox/personas", json={"form": "IP", "flags": ["liquidation"]})
    assert wrong.status_code == 422 and wrong.json()["code"] == "FLAG_NOT_APPLICABLE"


async def test_invalid_inn_comes_with_a_valid_suggestion(stand):
    valid = world.inn_ul("770123456")
    broken = valid[:-1] + str((int(valid[-1]) + 1) % 10)
    resp = await stand.api.post("/sandbox/personas", json={"full_name": "Анна Петрова", "inn": broken})
    body = resp.json()
    assert resp.status_code == 422 and body["code"] == "INN_INVALID" and body["suggested_inn"] == valid


async def test_score_texts_only_for_factors_that_lower_the_score(stand):
    headers = await stand.login("s7")
    score = await stand.call("GET", f"/companies/{SMIRNOVA}/score", headers)
    for c in score["contributions"]:
        assert c["title"] and (c["text"] is not None) == (c["effect"] == "minus"), c


async def test_bank_metrics_measure_stp_and_decision_time(stand):
    client = await stand.login("s7")
    app = await stand.call("POST", "/applications", client, expect=201, json={
        "inn": SMIRNOVA, "product": "OVERDRAFT", "amount": 400000, "goal": "cash_gap", "consent_bki": True})
    await stand.call("POST", f"/applications/{app['id']}/submit", client)
    await stand.pump()
    denied = await stand.api.get("/bank/metrics", headers=client)
    assert denied.status_code == 403
    officer = await stand.login("bank")
    m = await stand.call("GET", "/bank/metrics", officer)
    assert m["applications"] == 1 and m["by_status"] == {"OFFERED": 1} and m["outcomes"] == {"APPROVE": 1}
    assert m["decisions"] == {"auto": 1, "manual": 0, "stp_share": 1.0}
    assert m["time_to_decision"]["count"] == 1 and m["time_to_decision"]["within_target"] == 1.0


async def test_new_public_contract_brings_a_contract_loan_signal(stand):
    headers = await stand.login("s5")
    before = await stand.call("GET", f"/companies/{HLEB}/insights", headers)
    assert before["contract"] is None
    await stand.call("POST", "/sandbox/events", json={"type": "eis.contract_signed", "inn": HLEB, "amount": 15_000_000},
                     expect=202)
    await stand.pump()
    signal = (await stand.call("GET", f"/companies/{HLEB}/insights", headers))["contract"]
    assert signal["price"] == 15_000_000 and signal["advance_percent"] == 20
    assert signal["offer"]["product"] == "CONTRACT" and signal["offer"]["amount"] <= 15_000_000 * 0.8 * 0.7


async def test_audit_chain_is_intact_and_catches_tampering(stand):
    client = await stand.login("s7")
    await stand.call("POST", "/applications", client, expect=201,
                     json={"inn": SMIRNOVA, "product": "OVERDRAFT", "amount": 400000, "goal": "cash_gap"})
    officer = await stand.login("bank")
    check = await stand.call("GET", "/bank/audit", officer)
    assert check["intact"] and check["events"] > 0 and check["broken_at"] is None
    async with stand.pool.acquire() as conn:
        victim = await conn.fetchval("SELECT min(id) FROM events WHERE type = 'application.status_changed'")
        await conn.execute("""UPDATE events SET payload = jsonb_set(payload, '{to}', '"ISSUED"') WHERE id = $1""", victim)
    tampered = await stand.call("GET", "/bank/audit", officer)
    assert not tampered["intact"] and tampered["broken_at"] == victim
