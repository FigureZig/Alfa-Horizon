"""Контракт API без базы: конверт {data}, ошибки RFC 9457 с кодом, CORS для фронта, X-Request-Id."""

import httpx
import pytest

from app.main import app

pytestmark = pytest.mark.anyio
FRONT = "http://localhost:5173"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def api():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test/api/v1") as client:
        yield client


async def test_success_is_wrapped_in_data(api):
    assert (await api.get("/health/live")).json() == {"data": {"status": "ok"}}
    calc = await api.post("/calc/loan", json={"amount": 1_000_000, "term_months": 12, "rate": 20, "product": "EXPRESS"})
    assert calc.status_code == 200 and calc.json()["data"]["payment"] == "92634.51"     # деньги — строкой, без float


async def test_errors_are_problem_details_with_code(api):
    missing = await api.get("/nowhere")
    assert missing.status_code == 404 and missing.headers["content-type"].startswith("application/problem+json")
    assert missing.json()["code"] == "NOT_FOUND"
    invalid = await api.post("/calc/loan", json={"amount": -1})
    body = invalid.json()
    assert invalid.status_code == 422 and body["code"] == "VALIDATION_ERROR"
    assert {tuple(e["loc"]) for e in body["errors"]} >= {("body", "amount"), ("body", "term_months")}


async def test_cors_lets_the_frontend_in_and_request_id_is_echoed(api):
    preflight = await api.options("/sandbox/personas", headers={"Origin": FRONT, "Access-Control-Request-Method": "GET"})
    assert preflight.headers["access-control-allow-origin"] == FRONT
    assert (await api.get("/health/live", headers={"X-Request-Id": "abc"})).headers["x-request-id"] == "abc"
    stranger = await api.options("/health/live", headers={"Origin": "http://evil.example",
                                                           "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in stranger.headers


def test_every_operation_is_documented_for_swagger_and_redoc():
    """У каждой ручки — русское название и схема успешного ответа; ошибки — RFC 9457; есть схема входа Bearer."""
    spec = app.openapi()
    assert spec["components"]["securitySchemes"]["JWT"]["scheme"] == "bearer"
    assert {t["name"] for t in spec["tags"]} >= {"auth", "cabinet", "application", "bank", "simulator"}
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            assert any("а" <= ch <= "я" for ch in op["summary"].lower()), (method, path, op["summary"])
            ok = [c for c in op["responses"] if c.startswith("2")]
            assert ok, (method, path)
            content = op["responses"][ok[0]].get("content", {})
            if ok[0] != "204" and "text/event-stream" not in content:
                assert content["application/json"]["schema"]["$ref"], (method, path)
            for code, response in op["responses"].items():
                if code.startswith("4"):
                    assert list(response["content"]) == ["application/problem+json"], (method, path, code)


async def test_product_cards_for_the_landing_come_from_the_policy(api):
    data = (await api.get("/catalog/products", params={"lang": "ru"})).json()["data"]
    cards = {c["id"]: c for c in data["products"]}
    assert set(cards) == {"OVERDRAFT", "EXPRESS", "WORKING_CAPITAL", "INVESTMENT", "CONTRACT", "AGRO_SEASONAL"}
    key = data["key_rate"]["value"]
    for c in cards.values():
        parts = c["rate_parts"]
        assert c["rate_from"] == round(parts["key_rate"] + parts["industry"] + parts["risk"], 2) and c["rate_from"] > key
    assert cards["INVESTMENT"]["decision"] == "specialist" and cards["OVERDRAFT"]["decision"] == "auto"


async def test_smart_features_respect_their_flags(api):
    from app.config import settings

    saved = settings.features
    object.__setattr__(settings, "features", frozenset({"K1", "K2", "K3"}))
    try:
        resp = await api.get("/companies/770100000079/repayment", params={"amount": 100000})
        assert resp.status_code == 404 and resp.json()["code"] == "FEATURE_OFF"
    finally:
        object.__setattr__(settings, "features", saved)
