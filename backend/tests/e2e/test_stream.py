"""Живой таймлайн (SSE): пока клиент слушает поток, конвейер и подпись меняют статус — события приходят сразу,
поток закрывается на выдаче; переподключение с Last-Event-ID отдаёт пропущенное."""

import asyncio
import json

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.anyio]

SMIRNOVA = "770100000079"


def _events(text: str) -> list[tuple[str, dict]]:
    out = []
    for block in text.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if not line.startswith(":"))
        if "event" in fields:
            out.append((fields["event"], json.loads(fields["data"])))
    return out


async def test_status_changes_arrive_live_and_stream_ends_on_issue(stand):
    headers = await stand.login("s7")
    app = await stand.call("POST", "/applications", headers, expect=201, json={
        "inn": SMIRNOVA, "product": "OVERDRAFT", "amount": 400000, "goal": "cash_gap", "consent_bki": True})
    listening = asyncio.create_task(stand.api.get(f"/applications/{app['id']}/stream", headers=headers,
                                                  params={"timeout_s": 20}))
    await asyncio.sleep(0.3)
    await stand.call("POST", f"/applications/{app['id']}/submit", headers)
    await stand.pump()
    await stand.call("POST", f"/applications/{app['id']}/offer/accept", headers, json={"variant": 0})
    await stand.call("POST", f"/applications/{app['id']}/signatures", headers)
    await stand.pump()
    resp = await asyncio.wait_for(listening, 20)
    assert resp.headers["content-type"].startswith("text/event-stream")
    events = _events(resp.text)
    assert events[0] == ("snapshot", {"status": "DRAFT", "flags": [], "deadline": events[0][1]["deadline"]})
    path = [e["payload"]["to"] for kind, e in events if kind == "application.status_changed"]
    assert path == ["SUBMITTED", "CHECKING", "OFFERED", "SIGNING", "SIGNED", "DISBURSING", "ISSUED"]

    replay = await stand.api.get(f"/applications/{app['id']}/stream", headers={**headers, "Last-Event-ID": "0"},
                                 params={"timeout_s": 5})
    assert [e["payload"]["to"] for k, e in _events(replay.text) if k == "application.status_changed"][-1] == "ISSUED"
