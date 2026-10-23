"""16 сквозных прогонов из qa/graph.py через настоящий HTTP API: каждый переход графа статусов вызывается тем,
кто его делает в жизни, — клиентом, конвейером, таймером, специалистом банка или событием мира.

Маршруты не захардкожены: их считает задача китайского почтальона по таблице state.py. Новый переход без действия
в ACTIONS — тест упадёт и скажет, какого.
"""

from datetime import datetime

import pytest

from qa import graph
from seed import world

pytestmark = [pytest.mark.e2e, pytest.mark.anyio]

ROUTES = graph.covering_routes(graph.status_graph())
COMPANIES = {c["key"]: c for c in world.load()["companies"]}
# первый исход проверки в маршруте → кто подаёт и что: golden-сценарии демо-мира (seed/personas.yaml)
CASTING = {"OFFERED": ("s7", "smirnova"), "INFO_REQUESTED": ("s2", "masterstroy"), "UNDER_REVIEW": ("s5", "hleb"),
           "REJECTED": ("s4", "romashka")}
ANSWERS = {"REQ_CORP_APPROVAL": {"corporate_approval": True}, "REQ_COLLATERAL_VALUE": {"collateral_value": 1_500_000}}


class Run:
    def __init__(self, stand, app_id: str, inn: str, company_key: str, client: dict, bank: dict):
        self.stand, self.app_id, self.inn, self.company_key = stand, app_id, inn, company_key
        self.client, self.bank, self.faults = client, bank, []

    async def act(self, action: str, headers: dict, json=None):
        return await self.stand.call("POST", f"/applications/{self.app_id}/{action}", headers, json=json)

    async def application(self) -> dict:
        return await self.stand.call("GET", f"/applications/{self.app_id}", self.client)

    async def fault(self, source: str, inn: str | None = None) -> None:
        f = await self.stand.call("POST", "/sandbox/faults", json={"source": source, "mode": "error503", "inn": inn})
        self.faults.append(f["id"])

    async def clear_faults(self) -> None:
        for fault_id in self.faults:
            await self.stand.call("DELETE", f"/sandbox/faults/{fault_id}")
        self.faults = []

    async def event(self, harmful: bool) -> None:
        """Событие мира: банкротство (стоп) или небольшая недоимка ниже порога политики (пересмотр без отказа)."""
        body = {"type": "legal.bankruptcy_started", "inn": self.inn} if harmful else \
            {"type": "fns.tax_debt_appeared", "inn": self.inn, "amount": 10_000}
        await self.stand.call("POST", "/sandbox/events", json=body)


async def submit(run, nxt):
    await run.act("submit", run.client)


async def withdraw(run, nxt):
    await run.act("withdraw", run.client)


async def one_job(run, nxt):
    assert await run.stand.step()


async def decision(run, nxt, outcome):
    if outcome == "REJECTED" and run.company_key != "romashka":     # отказ после пересмотра — нужен стоп-фактор
        await run.event(harmful=True)
    await run.stand.until_left(run.app_id, "CHECKING")


async def answer_data(run, nxt):
    """Ответ данными, которые понимает движок (решение участников, стоимость залога) → проверка заново."""
    asked = (await run.application())["info_request"]
    body = {k: v for ask in asked["asks"] for k, v in ANSWERS[ask].items()}
    await run.act("info-requests/answer", run.client, body)


async def answer_documents(run, nxt):
    """Только документы и пояснение — смотрит специалист."""
    await run.act("info-requests/answer", run.client, {"documents": ["Пояснения к отчётности.pdf"], "comment": "Пояснения"})


async def expire(run, nxt):
    """Перемотка часов мира ровно за срок текущего статуса: сроки как в бою (дни), ждать их тест не может."""
    deadline = (await run.application())["deadline"]
    now = (await run.stand.call("GET", "/sandbox/clock"))["now"]
    left = datetime.fromisoformat(deadline["at"]) - datetime.fromisoformat(now)
    await run.stand.advance(int(left.total_seconds()) + 60)


async def bank(run, nxt, action):
    body = {"action": action, "comment": "решение специалиста в e2e"}
    if action == "request_info":
        body["asks"] = ["REQ_COLLATERAL_VALUE"] if nxt == "CHECKING" else ["REQ_DOCUMENTS"]
    await run.stand.call("POST", f"/bank/applications/{run.app_id}/decision", run.bank, json=body)


async def accept(run, nxt):
    await run.act("offer/accept", run.client, {"variant": 0})


async def decline(run, nxt):
    await run.act("offer/decline", run.client)


async def recheck(run, nxt):
    await run.event(harmful=nxt == "REJECTED")
    status = await run.stand.status(run.app_id)
    await run.stand.until_left(run.app_id, status)


async def sign(run, nxt):
    await run.act("signatures", run.client)


async def disburse(run, nxt):
    if nxt == "UNDER_REVIEW":                                      # АБС не подтверждает выдачу (N7)
        await run.fault("abs")
    await run.stand.until_left(run.app_id, "SIGNED")
    await run.clear_faults()


async def final_stop(run, nxt):
    await run.event(harmful=True)                                  # банкротство после подписи (N17)
    await run.stand.until_left(run.app_id, "SIGNED")


async def final_check_down(run, nxt):
    await run.fault("legal", run.inn)                              # юр. проверки молчат перед выдачей (N6)
    await run.stand.until_left(run.app_id, "SIGNED", fast_forward=True)
    await run.clear_faults()


ACTIONS = {
    ("DRAFT", "SUBMITTED"): submit,
    ("SUBMITTED", "CHECKING"): one_job,
    ("CHECKING", "OFFERED"): lambda run, nxt: decision(run, nxt, "OFFERED"),
    ("CHECKING", "INFO_REQUESTED"): lambda run, nxt: decision(run, nxt, "INFO_REQUESTED"),
    ("CHECKING", "UNDER_REVIEW"): lambda run, nxt: decision(run, nxt, "UNDER_REVIEW"),
    ("CHECKING", "REJECTED"): lambda run, nxt: decision(run, nxt, "REJECTED"),
    ("INFO_REQUESTED", "CHECKING"): answer_data,
    ("INFO_REQUESTED", "UNDER_REVIEW"): answer_documents,
    ("INFO_REQUESTED", "EXPIRED"): expire,
    ("UNDER_REVIEW", "OFFERED"): lambda run, nxt: bank(run, nxt, "approve"),
    ("UNDER_REVIEW", "INFO_REQUESTED"): lambda run, nxt: bank(run, nxt, "request_info"),
    ("UNDER_REVIEW", "REJECTED"): lambda run, nxt: bank(run, nxt, "reject"),
    ("OFFERED", "SIGNING"): accept,
    ("OFFERED", "DECLINED"): decline,
    ("OFFERED", "EXPIRED"): expire,
    ("OFFERED", "CHECKING"): recheck,
    ("SIGNING", "SIGNED"): sign,
    ("SIGNING", "EXPIRED"): expire,
    ("SIGNING", "CHECKING"): recheck,
    ("SIGNED", "DISBURSING"): disburse,
    ("SIGNED", "REJECTED"): final_stop,
    ("SIGNED", "UNDER_REVIEW"): final_check_down,
    **{(src, "WITHDRAWN"): withdraw for src in ("DRAFT", "SUBMITTED", "CHECKING", "INFO_REQUESTED", "UNDER_REVIEW",
                                                 "OFFERED", "SIGNING", "SIGNED")},
}


def test_every_transition_has_an_action():
    chained = {("DISBURSING", "ISSUED"), ("DISBURSING", "UNDER_REVIEW")}     # тот же шаг выдачи, что и SIGNED → DISBURSING
    assert set(ACTIONS) | chained == set(graph.status_graph().edges)


@pytest.mark.parametrize("route", ROUTES, ids=[f"{i + 1:02d}-{r[-1]}-{len(r) - 1}" for i, r in enumerate(ROUTES)])
async def test_route(stand, route):
    first = next((b for a, b in zip(route, route[1:], strict=False) if a == "CHECKING"), "OFFERED")
    persona, company_key = CASTING[first]
    company = COMPANIES[company_key]
    client, bank_headers = await stand.login(persona), await stand.login("bank")
    created = await stand.call("POST", "/applications", client,
                               json={"inn": company["inn"], **company["scenario"]["request"], "consent_bki": True})
    run = Run(stand, created["id"], company["inn"], company_key, client, bank_headers)

    seen = ["DRAFT"]
    while len(seen) < len(route):
        src, dst = route[len(seen) - 1], route[len(seen)]
        nxt = route[len(seen) + 1] if len(seen) + 1 < len(route) else None
        await ACTIONS[(src, dst)](run, nxt)
        new = (await stand.path(run.app_id))[len(seen):]
        assert new and route[len(seen):len(seen) + len(new)] == new, \
            f"{src} → {dst}: ждали {route[len(seen):]}, получили {new}; пройдено {seen}"
        seen += new
    assert seen == route
    # реестр банка: «решил специалист» — только если на маршруте было его решение, «решил движок» — только окончательный исход
    row = next(r for r in await stand.call("GET", "/bank/applications", bank_headers, params={"q": company["inn"]})
               if r["id"] == run.app_id)
    banked = any(a == "UNDER_REVIEW" and b in ("OFFERED", "INFO_REQUESTED", "REJECTED")
                 for a, b in zip(route, route[1:], strict=False))
    assert (row["decided_by"] == "bank") == banked
    assert row["decided_by"] != "engine" or row["outcome"] in {"APPROVE", "APPROVE_WITH_CONDITIONS", "COUNTER_OFFER", "REJECT"}
