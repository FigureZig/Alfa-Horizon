"""Сценарии ролей из seed/flows.py через HTTP API: каждый шаг — от лица своего пользователя, и перед шагом он входит
заново, как проверяющий в интерфейсе. Перелогин не меняет мир: события реестров и отказы из панели остаются до сброса.
После шага сверяется статус заявки. «Нельзя» проверяется честно: запрос уходит и получает 403."""

import pytest

from seed import world
from seed.flows import FLOWS

pytestmark = [pytest.mark.e2e, pytest.mark.anyio]
COMPANIES = {c["key"]: c for c in world.load()["companies"]}
DOCUMENTS = {"documents": ["Пояснения к отчётности.pdf"], "comment": "Пояснения по запросу специалиста"}


async def _forbidden(stand, headers: dict, action: str, inn: str, app_id: str | None, request: dict):
    calls = {"create": ("POST", "/applications", {"inn": inn, **request}),
             "sign": ("POST", f"/applications/{app_id}/signatures", None),
             "confirm": ("POST", f"/bank/applications/{app_id}/decision/confirm", {"approve": True})}
    method, path, body = calls[action]
    resp = await stand.api.request(method, path, headers=headers, json=body)
    assert resp.status_code == 403, (action, resp.status_code, resp.text)


@pytest.mark.parametrize("flow", FLOWS, ids=[f.id for f in FLOWS])
async def test_flow(stand, flow):
    company = COMPANIES[flow.company]
    request = flow.request or company["scenario"]["request"]
    app_id = None
    for n, step in enumerate(flow.steps, 1):
        headers = await stand.login(step.user) if step.user != "system" else None     # перелогин перед каждым шагом
        base = f"/applications/{app_id}"
        match step.action:
            case "create":
                app_id = (await stand.call("POST", "/applications", headers, expect=201,
                                           json={"inn": company["inn"], **request, "consent_bki": True}))["id"]
            case "submit" | "withdraw":
                await stand.call("POST", f"{base}/{step.action}", headers)
            case "run":
                await stand.pump()
            case "vote":
                await stand.call("POST", f"{base}/approvals/vote", headers, json={"vote": step.arg})
            case "accept":
                await stand.call("POST", f"{base}/offer/accept", headers, json={"variant": 0})
            case "decline":
                await stand.call("POST", f"{base}/offer/decline", headers)
            case "sign":
                await stand.call("POST", f"{base}/signatures", headers)
            case "answer":
                await stand.call("POST", f"{base}/info-requests/answer", headers,
                                 json=DOCUMENTS if step.arg == "documents" else {"corporate_approval": True})
            case "bank":
                body = {"action": step.arg, "comment": "решение специалиста"}
                if step.arg == "request_info":
                    body["asks"] = ["REQ_DOCUMENTS"]
                await stand.call("POST", f"/bank{base}/decision", headers, json=body)
            case "confirm":
                await stand.call("POST", f"/bank{base}/decision/confirm", headers, json={"approve": step.arg})
            case "event":
                await stand.call("POST", "/sandbox/events", json={"type": step.arg, "inn": company["inn"]}, expect=202)
                await stand.pump()
            case "forbidden":
                await _forbidden(stand, headers, step.arg, company["inn"], app_id, request)
            case _:
                raise AssertionError(f"неизвестное действие {step.action}")
        if step.status:
            assert await stand.status(app_id) == step.status, f"{flow.id} шаг {n} ({step.user} {step.action}): {step.note}"
