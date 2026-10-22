"""Гид GET /sandbox/scenarios исполним буквально: каждый сценарий проходится только по его подсказкам — кем войти, какой
запрос отправить, какой HTTP-код и статус заявки ожидать. Так по нему может идти и проверяющий в Swagger, и фронт."""

import pytest

from seed.flows import FLOWS

pytestmark = [pytest.mark.e2e, pytest.mark.anyio]


@pytest.mark.parametrize("flow_id", [f.id for f in FLOWS])
async def test_guide_walks_through(stand, flow_id):
    guide = next(s for s in await stand.call("GET", "/sandbox/scenarios") if s["id"] == flow_id)
    tokens = {user: await stand.login(user) for user in guide["users"]}
    app_id = None
    for step in guide["steps"]:
        api = step["api"]
        if step["action"] == "run":
            await stand.pump()
        else:
            path = api["path"].replace("{application_id}", str(app_id)).removeprefix("/api/v1")
            headers = tokens[step["user"]["id"]] if step["user"] else None
            resp = await stand.api.request(api["method"], path, headers=headers, json=api["body"])
            assert resp.status_code == step["expect_http"], (flow_id, step["n"], resp.text)
            if step["action"] == "create":
                app_id = resp.json()["data"]["id"]
            if step["action"] == "event":
                await stand.pump()
        if step["expect_status"]:
            assert await stand.status(app_id) == step["expect_status"], (flow_id, step["n"], step["note"])
