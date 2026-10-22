"""Кабинет компании по ИНН в контракте фронта (frontend/src/app/types): ключи DTO, значения enum и числа K1 у S7."""

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.anyio]

SMIRNOVA = "770100000079"
FRONT_STATUS = {"DRAFT", "SUBMITTED", "IN_REVIEW", "ACTION_REQUIRED", "APPROVED", "REJECTED", "ISSUED"}


async def test_home_widgets_and_forecast(stand):
    headers = await stand.login("s7")
    user = await stand.call("GET", f"/demo-personas/{SMIRNOVA}", headers)
    assert {"inn", "first_name", "last_name", "initials", "organization_name"} <= set(user)
    assert (user["first_name"], user["initials"]) == ("Анна", "АС")

    cards = await stand.call("GET", f"/demo-personas/{SMIRNOVA}/dashboard/summary", headers)
    assert [c["type"] for c in cards] == ["balance", "outflow", "inflow"]
    assert all({"id", "title", "amount", "currency", "description"} <= set(c) and isinstance(c["amount"], float) for c in cards)

    fc = (await stand.call("GET", f"/companies/{SMIRNOVA}/insights", headers))["cash_forecast"]
    assert {"status", "horizon_days", "currency", "points", "cash_gap", "operations"} <= set(fc)
    assert (fc["status"], fc["horizon_days"], fc["cash_gap"]["date"]) == ("CASH_GAP", 30, "2026-10-28")
    assert abs(fc["cash_gap"]["amount"]) == 36195.64                    # аренда и зарплата 25-го, поставщики 27-го, налоги 28-го
    assert all(op["date"] <= "2026-10-28" and {"id", "title", "amount"} <= set(op) for op in fc["operations"])

    products = await stand.call("GET", f"/companies/{SMIRNOVA}/products", headers)
    keys = {"id", "name", "amount", "currency", "rate", "is_rate_from", "term_months", "benefits", "is_preliminary",
            "is_recommended"}
    assert products and all(keys <= set(p) for p in products)
    recommended = [p for p in products if p["is_recommended"]]
    assert len(recommended) == 1 and recommended[0]["amount"] >= abs(fc["cash_gap"]["amount"])

    profile = await stand.call("GET", f"/companies/{SMIRNOVA}/profile", headers)
    assert profile["legal_form"] == "IP" and set(profile["sources"]) <= {"EGRUL", "FNS", "BANK_ACCOUNT", "CREDIT_BUREAU"}
    assert profile["tax_regime"] in {"USN", "OSN", "PSN", "ESHN", "AUSN", None} and profile["activity"]["okved_code"]

    score = await stand.call("GET", f"/companies/{SMIRNOVA}/score", headers)
    assert score["class"] in "ABCD" and score["contributions"] and "levers" in score

    plan = await stand.call("GET", f"/companies/{SMIRNOVA}/repayment", headers, params={"amount": 400000, "term_months": 12})
    assert plan["recommendation"] in ("fixed", "from_inflows") and plan["fixed"]["payment"] > 0 and plan["why"]


async def test_applications_summary_and_tasks(stand):
    headers = await stand.login("s7")
    app = await stand.call("POST", "/applications", headers, json={"inn": SMIRNOVA, "product": "OVERDRAFT", "amount": 400000,
                                                                   "goal": "cash_gap", "consent_bki": True}, expect=201)
    await stand.call("POST", f"/applications/{app['id']}/submit", headers)
    await stand.pump()
    await stand.call("POST", f"/applications/{app['id']}/offer/accept", headers)

    summary = await stand.call("GET", f"/companies/{SMIRNOVA}/applications/summary", headers)
    item = next(a for a in summary["applications"] if a["id"] == app["id"])
    assert {"id", "product_name", "amount", "currency", "status", "updated_at"} <= set(item)
    assert item["status"] in FRONT_STATUS and (item["status"], item["status_detail"]) == ("ACTION_REQUIRED", "SIGNING")
    assert {t["type"] for t in summary["tasks"]} <= {"SIGNATURE", "DOCUMENT_REQUEST"}
    sign = next(t for t in summary["tasks"] if t["application_id"] == app["id"])
    assert sign["type"] == "SIGNATURE" and {"id", "title", "due_date"} <= set(sign)

    inbox = await stand.call("GET", "/tasks", headers)
    assert any(t["application_id"] == app["id"] and t["action"] == "sign" for t in inbox)
