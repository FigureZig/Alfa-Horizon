"""Жизненный цикл заявки (docs/02 §6, docs/05 §2 и §7, docs/07): подача, оферта, подпись, выдача, дозапрос,
решение специалиста, отзыв, пересмотр, сроки.

Статус проверяет таблица state.py, событие пишется в той же транзакции, что и заявка. Права проверяет API
(app/api/deps.py) до вызова команды; здесь — правила процесса. Долгие шаги (конвейер, выдача) — задачи worker,
сроки — sweeper по часам симулятора (app/clock.py).
"""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx

from . import clock, company, sources, store
from .config import settings
from .domain import engine, state
from .domain.rights import signed_enough, signers
from .errors import Problem
from .jsonutil import plain
from .policy import load as load_policy
from .policy import sources as source_config

# статус со сроком → вид срока в policy.timers и куда заявка уходит, когда срок истёк
TIMED = {"DRAFT": ("draft", "WITHDRAWN"), "OFFERED": ("offer", "EXPIRED"), "SIGNING": ("signing", "EXPIRED"),
         "INFO_REQUESTED": ("info", "EXPIRED")}
REGISTRY = ("egrul", "egrip")
FINAL_CHECK = ("legal", "egrul", "egrip", "debtam")       # без свежих ответов не выдаём (docs/07 §4, BLOCK)
FINAL_CHECK_ATTEMPTS = 3
ANSWERS = {"REQ_CORP_APPROVAL": "corporate_approval", "REQ_COLLATERAL_VALUE": "collateral_value"}


class AbsUnavailable(Exception):
    pass


def timer_s(kind: str) -> int:
    t = load_policy()["timers"][kind]
    return t["demo"] if settings.demo_mode else t["prod"]


async def move(conn, app: dict, to: str, actor: str, *, flags=None, patch: dict | None = None, reason: str | None = None,
               idempotency_key: str | None = None) -> dict:
    """Переход + срок нового статуса (или снять старый) + SLA ручного рассмотрения."""
    now, patch = await clock.now(conn), dict(patch or {})
    timed = TIMED.get(to)
    patch["deadline"] = None if timed is None else {
        "status": to, "at": (now + timedelta(seconds=timer_s(timed[0]))).isoformat(), "then": timed[1]}
    if to == "UNDER_REVIEW":
        patch["sla_until"] = (now + timedelta(seconds=timer_s("manual_sla"))).isoformat()
    return await store.move(conn, app, to, actor, flags=flags, data_patch=patch, reason=reason, idempotency_key=idempotency_key)


async def load(conn, app_id) -> dict:
    app = await store.get_application(conn, app_id)
    if app is None:
        raise Problem(404, "APPLICATION_NOT_FOUND", "заявка не найдена")
    return app


def expect(app: dict, *statuses: str) -> None:
    if app["status"] not in statuses:
        raise Problem(409, "INVALID_STATUS", f"действие недоступно в статусе {app['status']}", app_status=app["status"])


def offers(app: dict) -> list[dict]:
    decision = app["data"].get("decision") or {}
    return [o for o in [decision.get("offer"), *decision.get("alternatives", [])] if o]


def actions(app: dict, can: dict | None = None, *, role: str = "client", person_inn: str | None = None) -> list[str]:
    """Что текущий пользователь может сделать с заявкой сейчас — фронт рисует кнопки по этому списку."""
    status, can, data = app["status"], can or {}, app["data"]
    pending = data.get("pending_decision")
    if role in ("loan_officer", "risk_manager"):
        if status != "UNDER_REVIEW":
            return []
        return (["decide"] if not pending else []) + (["confirm"] if pending and role == "risk_manager" else [])
    out, by_status = [], {"DRAFT": ["submit"], "OFFERED": ["accept_offer", "decline_offer"], "INFO_REQUESTED": ["answer_info"]}
    if can.get("prepare"):
        out += by_status.get(status, [])
        out += ["withdraw"] * state.can(status, "WITHDRAWN")
    if can.get("sign") and status == "SIGNING" and "PROVISIONAL" not in app["flags"] \
            and person_inn not in {s["inn"] for s in data.get("signatures", [])}:   # уже подписал — ждём остальных
        out.append("sign")
    approval = data.get("approval") or {}
    if status == "INFO_REQUESTED" and can.get("approve") and approval.get("status") == "open" \
            and approval.get("method") == "electronic" and person_inn in {p["inn"] for p in approval["participants"]} \
            and person_inn not in {v["inn"] for v in approval["votes"]}:
        out.append("vote")
    return out


# ── команды клиента ──────────────────────────────────────────────────────────────────────────────────────────────


async def create(conn, inn: str, request: dict, consent_bki: bool, actor: str, created_by: dict,
                 company_name: str | None = None) -> dict:
    """company_name — название на момент подачи: реестр банка покажет его, даже если свою компанию потом удалили."""
    now = await clock.now(conn)
    deadline = {"status": "DRAFT", "at": (now + timedelta(seconds=timer_s("draft"))).isoformat(), "then": "WITHDRAWN"}
    data = {"request": request, "consent_bki": consent_bki, "created_by": created_by, "deadline": deadline,
            "company_name": company_name}
    return await store.create_application(conn, inn, data, actor)


async def submit(conn, app: dict, actor: str, idempotency_key: str | None = None) -> dict:
    """DRAFT → SUBMITTED и задача конвейера в одной транзакции. Повтор безопасен: поданную заявку не трогаем."""
    if app["status"] != "DRAFT":
        return app
    async with conn.transaction():
        app = await move(conn, app, "SUBMITTED", actor, reason="подана", idempotency_key=idempotency_key)
        await store.enqueue(conn, "pipeline", application_id=app["id"])
    return app


async def withdraw(conn, app: dict, actor: str) -> dict:
    """Отозвать можно до выдачи; после подписи это отказ от получения (ГК ст. 821 п. 2)."""
    if not state.can(app["status"], "WITHDRAWN"):
        raise Problem(409, "CANNOT_WITHDRAW", "отозвать нельзя: деньги уже выдаются или заявка завершена",
                      app_status=app["status"])
    return await move(conn, app, "WITHDRAWN", actor, reason="отозвана клиентом")


async def accept_offer(conn, app: dict, actor: str, variant: int = 0) -> dict:
    expect(app, "OFFERED")
    options = offers(app)
    if not 0 <= variant < len(options):
        raise Problem(422, "OFFER_VARIANT_UNKNOWN", f"варианта {variant} нет: доступно {len(options)}")
    facts, _ = await company.facts(conn, app["company_inn"])
    patch = {"offer": {**options[variant], "variant": variant}, "signers": signers(facts), "signatures": []}
    return await move(conn, app, "SIGNING", actor, patch=patch, reason="оферта принята")


async def decline_offer(conn, app: dict, actor: str) -> dict:
    expect(app, "OFFERED")
    return await move(conn, app, "DECLINED", actor, reason="клиент отказался от оферты")


async def sign(conn, app: dict, actor: str, person: dict) -> dict:
    """person = {inn, fio, role}; право подписи уже проверено. Совместные ЕИО — договор подписан, когда подписали все."""
    expect(app, "SIGNING")
    if "PROVISIONAL" in app["flags"]:
        raise Problem(409, "BKI_PENDING", "подписать можно после проверки кредитной истории — условия пока предварительные")
    snaps = await store.snapshots(conn, app["company_inn"])
    registry = next((snaps[s] for s in REGISTRY if s in snaps), None)
    stale = registry is None or registry["error"] or \
        datetime.now(UTC) - registry["fetched_at"] > timedelta(seconds=timer_s("fresh_before_signing"))
    if stale:                                                  # полномочия — только по свежей выписке (docs/07 N3)
        await store.enqueue(conn, "refresh_company", {"inn": app["company_inn"]})
        raise Problem(409, "SOURCE_WAIT", "проверяем полномочия по свежей выписке из реестра — повторите подпись через минуту")
    signatures = app["data"].get("signatures", [])
    if person["inn"] in {s["inn"] for s in signatures}:
        return app
    signatures = [*signatures, {**person, "at": (await clock.now(conn)).isoformat()}]
    facts, _ = await company.facts(conn, app["company_inn"])
    if not signed_enough(facts, {s["inn"] for s in signatures}):
        return await store.patch(conn, app, actor, "signature.added", {"inn": person["inn"], "role": person["role"]},
                                 data_patch={"signatures": signatures})
    async with conn.transaction():
        app = await move(conn, app, "SIGNED", actor, patch={"signatures": signatures}, reason="договор подписан")
        await store.enqueue(conn, "disburse", application_id=app["id"])
    return app


async def answer_info(conn, app: dict, actor: str, answer: dict) -> dict:
    """Ответ на дозапрос. Просили то, что движок понимает (решение участников, стоимость залога), и ответ это закрыл —
    проверка заново, кто бы ни спросил; иначе документы смотрит специалист."""
    expect(app, "INFO_REQUESTED")
    asked = app["data"].get("info_request") or {"from": "system", "asks": (app["data"].get("decision") or {}).get("asks", [])}
    request = dict(app["data"]["request"])
    if answer.get("corporate_approval"):
        request["corporate_approval"] = True
    if answer.get("collateral_value"):
        request["collateral_value"] = answer["collateral_value"]
    closed = bool(asked["asks"]) and all(ANSWERS.get(a) and request.get(ANSWERS[a]) for a in asked["asks"])
    patch = {"request": request, "info_request": {**asked, "answer": answer, "answered_at": (await clock.now(conn)).isoformat()}}
    approval = app["data"].get("approval")
    if answer.get("corporate_approval") and approval and approval.get("status") == "open":
        patch["approval"] = {**approval, "status": "approved", "document": answer.get("documents") or ["решение участников"]}
    if closed:
        async with conn.transaction():
            app = await move(conn, app, "CHECKING", actor, patch=patch, reason="ответ на дозапрос — проверяем заново")
            await store.enqueue(conn, "decide", application_id=app["id"])
        return app
    return await move(conn, app, "UNDER_REVIEW", actor, patch=patch, reason="ответ на дозапрос — у специалиста")


# ── решение специалиста ──────────────────────────────────────────────────────────────────────────────────────────


async def bank_decide(conn, app: dict, actor: str, action: str, *, amount=None, term_months=None, comment: str | None = None,
                      asks: list[str] | None = None, role: str = "loan_officer") -> dict:
    """Одобрить (как предложил движок или с другой суммой и сроком по той же цене риска), отказать или дозапросить."""
    expect(app, "UNDER_REVIEW")
    if app["data"].get("pending_decision"):
        raise Problem(409, "AWAITING_SECOND_KEY", "решение ждёт подтверждения риск-менеджера")
    note = {"action": action, "comment": comment, "by": actor, "at": (await clock.now(conn)).isoformat()}
    if action == "reject":
        return await move(conn, app, "REJECTED", actor, flags=[], patch={"bank_decision": note},
                          reason=comment or "отказ специалиста")
    if action == "request_info":
        info = {"from": "bank", "asks": asks or ["REQ_DOCUMENTS"], "comment": comment}
        return await move(conn, app, "INFO_REQUESTED", actor, patch={"bank_decision": note, "info_request": info},
                          reason="дозапрос специалиста")
    decision = dict(app["data"].get("decision") or {})
    offer = decision.get("offer")
    if amount is not None or term_months is not None or offer is None:
        base, request = offer or {}, app["data"]["request"]
        if amount is None and not base:
            raise Problem(422, "AMOUNT_REQUIRED", "у движка нет предложения — укажите сумму и срок")
        facts, _ = await company.facts(conn, app["company_inn"])
        offer = engine.manual_terms(base.get("product") or request["product"],
                                    amount if amount is not None else base["amount"],
                                    term_months or base.get("term_months") or request.get("term_months"),
                                    facts, load_policy(), (decision.get("risk") or {}).get("class"))
    limit = load_policy()["params"]["specialist_authority_max"]
    if role == "loan_officer" and Decimal(str(offer["amount"])) > limit:     # выше полномочий — нужен второй ключ
        pending = {**note, "offer": offer, "limit": limit}
        return await store.patch(conn, app, actor, "decision.awaiting_second_key",
                                 {"amount": str(offer["amount"]), "limit": limit}, data_patch={"pending_decision": pending})
    return await _approve(conn, app, actor, offer, note)


async def _approve(conn, app: dict, actor: str, offer: dict, note: dict) -> dict:
    decision = dict(app["data"].get("decision") or {})
    decision.update(outcome="APPROVE", offer_kind="AS_REQUESTED", status="OFFERED", offer=offer, alternatives=[],
                    decided_by="bank")
    patch = {"decision": decision, "bank_decision": {**note, "offer": offer}, "pending_decision": None}
    return await move(conn, app, "OFFERED", actor, flags=[], patch=patch, reason="одобрено банком")


async def confirm(conn, app: dict, actor: str, approve: bool, comment: str | None = None) -> dict:
    """Второй ключ: риск-менеджер подтверждает одобрение специалиста выше его порога или возвращает его.
    Подтверждает другой человек — принцип четырёх глаз."""
    expect(app, "UNDER_REVIEW")
    pending = app["data"].get("pending_decision")
    if not pending:
        raise Problem(409, "NOTHING_TO_CONFIRM", "решения на подтверждение нет")
    if pending["by"] == actor:
        raise Problem(409, "SAME_PERSON", "второй ключ ставит другой сотрудник")
    note = {"action": "confirm" if approve else "return", "comment": comment, "by": actor,
            "at": (await clock.now(conn)).isoformat(), "first_key": pending["by"]}
    if approve:
        return await _approve(conn, app, actor, pending["offer"], {**pending, "second_key": note})
    return await store.patch(conn, app, actor, "decision.second_key_returned", {"comment": comment},
                             data_patch={"pending_decision": None, "returned_decision": {**pending, "returned": note}})


# ── согласие участников на крупную сделку ────────────────────────────────────────────────────────────────────────


def approval_for(facts: dict) -> dict:
    """Кто голосует и как: общее собрание участников ООО (14-ФЗ ст. 46 п. 3), голоса — по долям (ст. 32 п. 1).
    Электронные бюллетени — если устав допускает (ст. 38 п. 2, ГК ст. 67.1 п. 3 пп. 3); иначе нотариус.
    У АО акционеры в ЕГРЮЛ не видны — решение совета директоров или собрания акционеров (208-ФЗ ст. 79) документом."""
    method = (facts.get("charter") or {}).get("decisionMethod")
    if facts.get("segment") != "LLC":
        kind = "shareholders"
    else:
        kind = "notary" if method == "notary" else "electronic"
    return {"method": kind, "threshold_pct": load_policy()["params"]["approval_majority_pct"],
            "participants": [{"inn": p["inn"], "fio": p["fio"], "share": p["share"]} for p in facts.get("participants", [])],
            "votes": [], "for_pct": 0, "against_pct": 0, "status": "open"}


async def vote(conn, app: dict, actor: str, person: dict, choice: str) -> dict:
    """Голос участника. «За» больше порога — согласие получено, проверка заново; согласие уже недостижимо — заявка
    закрывается: без решения участников крупную сделку банк не заключает (сделка была бы оспоримой, ГК ст. 173.1)."""
    expect(app, "INFO_REQUESTED")
    approval = dict(app["data"].get("approval") or {})
    if approval.get("status") != "open":
        raise Problem(409, "NO_OPEN_APPROVAL", "голосование не открыто")
    if approval["method"] != "electronic":
        raise Problem(409, "NOTARY_REQUIRED" if approval["method"] == "notary" else "SHAREHOLDERS_DECISION_REQUIRED",
                      "по уставу решение удостоверяет нотариус — загрузите свидетельство" if approval["method"] == "notary"
                      else "решение акционеров загружается документом")
    member = next((p for p in approval["participants"] if p["inn"] == person["inn"]), None)
    if member is None:
        raise Problem(403, "NOT_A_PARTICIPANT", "голосуют участники общества")
    votes = [v for v in approval["votes"] if v["inn"] != person["inn"]]
    votes.append({**member, "vote": choice, "at": (await clock.now(conn)).isoformat()})
    total = sum(p["share"] for p in approval["participants"]) or 100
    for_pct = round(100 * sum(v["share"] for v in votes if v["vote"] == "for") / total, 2)
    against_pct = round(100 * sum(v["share"] for v in votes if v["vote"] == "against") / total, 2)
    threshold = approval["threshold_pct"]
    approval.update(votes=votes, for_pct=for_pct, against_pct=against_pct)
    if for_pct > threshold:
        approval["status"] = "approved"
        request = {**app["data"]["request"], "corporate_approval": True}
        async with conn.transaction():
            app = await move(conn, app, "CHECKING", actor, patch={"approval": approval, "request": request},
                             reason=f"участники согласовали крупную сделку: «за» {for_pct:g}% голосов")
            await store.enqueue(conn, "decide", application_id=app["id"])
        return app
    if 100 - against_pct <= threshold:
        approval["status"] = "rejected"
        return await move(conn, app, "WITHDRAWN", actor, patch={"approval": approval},
                          reason=f"участники не согласовали крупную сделку: «против» {against_pct:g}% голосов")
    return await store.patch(conn, app, actor, "approval.voted", {"inn": person["inn"], "vote": choice, "for_pct": for_pct,
                                                                  "against_pct": against_pct}, data_patch={"approval": approval})


# ── шаги worker ──────────────────────────────────────────────────────────────────────────────────────────────────


async def start_checking(conn, app: dict) -> None:
    """Шаг 1 конвейера: SUBMITTED → CHECKING; решение — отдельной задачей (чекпоинт, docs/07 §1)."""
    if app["status"] != "SUBMITTED":
        return
    async with conn.transaction():
        app = await move(conn, app, "CHECKING", "worker", reason="старт конвейера")
        await store.enqueue(conn, "decide", application_id=app["id"])


async def decide(conn, client: httpx.AsyncClient, app: dict) -> None:
    """Шаг 2: свежие данные → факты → решение → статус. Решённую или отозванную заявку не трогаем."""
    if app["status"] != "CHECKING":
        return
    inn = app["company_inn"]
    await store.add_event(conn, "step.changed", "worker", {"step": "sources", "state": "RUNNING"}, app["id"])
    fetched = await sources.refresh(conn, client, inn, with_bki=bool(app["data"].get("consent_bki")))
    await store.add_event(conn, "step.changed", "worker", {"step": "sources", "state": "DONE", "sources": fetched}, app["id"])
    facts, _ = await company.facts(conn, inn)
    decision = engine.decide(facts, app["data"]["request"], load_policy(), mode="commit")
    flags = list(dict.fromkeys(decision["flags"] + ["DEGRADED_DATA"] * bool(facts["degraded"])
                               + ["RECHECK"] * ("RECHECK" in app["flags"])))
    patch = {"decision": decision}
    if decision["outcome"] == "REQUEST_INFO":
        patch["info_request"] = {"from": "system", "asks": decision["asks"]}
        if "REQ_CORP_APPROVAL" in decision["asks"]:
            patch["approval"] = approval_for(facts)
    async with conn.transaction():
        app = await store.get_application(conn, app["id"])
        if app["status"] != "CHECKING":
            return
        await store.add_event(conn, "decision.made", "engine", {
            "outcome": decision["outcome"], "offer_kind": decision["offer_kind"], "policy_version": decision["policy_version"],
            "reasons": decision["reasons"], "flags": flags}, app["id"])
        await move(conn, app, decision["status"], "engine", flags=flags, patch=patch, reason=decision["outcome"])


async def disburse(conn, client: httpx.AsyncClient, app: dict) -> None:
    """После подписи: финальная проверка на свежих данных (ГК ст. 821 п. 1) → АБС с ключом идемпотентности → ISSUED."""
    if app["status"] != "SIGNED":
        return
    inn = app["company_inn"]
    fetched = await sources.refresh(conn, client, inn)
    if any(fetched.get(s) in ("error", "breaker_open") for s in FINAL_CHECK):
        attempts = app["data"].get("final_check_attempts", 0) + 1
        if attempts >= FINAL_CHECK_ATTEMPTS:          # N6: без перепроверки не выдаём — к специалисту
            await move(conn, app, "UNDER_REVIEW", "worker", flags=sorted({*app["flags"], "SOURCE_WAIT"}),
                       patch={"final_check_attempts": attempts}, reason="перед выдачей не ответили источники проверки")
            return
        await store.patch(conn, app, "worker", "step.changed", {"step": "final_check", "state": "WAITING", "sources": fetched},
                          flags=sorted({*app["flags"], "SOURCE_WAIT"}), data_patch={"final_check_attempts": attempts})
        await store.enqueue(conn, "disburse", application_id=app["id"], delay_s=5 if settings.demo_mode else 300)
        return
    facts, _ = await company.facts(conn, inn)
    stops = engine.stop_factors(facts, load_policy())
    if stops:                                                  # N17: всплыл стоп-фактор после подписи
        await move(conn, app, "REJECTED", "worker", patch={"final_check": {"stops": stops}},
                   reason="стоп-фактор при проверке перед выдачей (ГК ст. 821 п. 1)")
        return
    flags = [f for f in app["flags"] if f != "SOURCE_WAIT"]
    app = await move(conn, app, "DISBURSING", "worker", flags=flags, reason="проверка перед выдачей пройдена")
    try:
        loan = await abs_disburse(client, app)
    except AbsUnavailable as exc:
        await move(conn, app, "UNDER_REVIEW", "worker", flags=sorted({*flags, "DISBURSE_ERROR"}),
                   patch={"disburse_error": str(exc)}, reason="АБС не подтвердила выдачу — у специалиста")
        return
    now, repayment = await clock.now(conn), app["data"]["offer"]["repayment"]
    loan.update(disbursed_at=now.isoformat(), number=contract_number(app["id"], now), product=app["data"]["offer"]["product"],
                repayment=repayment, kind="limit" if repayment == "revolving" else "loan")   # овердрафт — лимит на счёте
    await move(conn, app, "ISSUED", "worker", patch={"loan": loan},
               reason="лимит подключён к счёту" if loan["kind"] == "limit" else "кредит выдан")


def contract_number(app_id, on: datetime) -> str:
    """Номер кредитного договора для клиента: год и начало id заявки — при повторе выдачи тот же самый."""
    return f"КД-{on.year}/{str(app_id).replace('-', '')[:6].upper()}"


async def abs_disburse(client: httpx.AsyncClient, app: dict) -> dict:
    """Открыть кредит и выдать. Ключ идемпотентности = id заявки: повтор не выдаст деньги дважды (docs/07 §7, F2)."""
    cfg, offer = source_config()["commands"]["abs"], app["data"]["offer"]
    url = settings.wiremock_url + cfg["path"]
    body = {"applicationId": str(app["id"]), "inn": app["company_inn"], "product": offer["product"],
            "amount": str(offer["amount"]), "termMonths": offer["term_months"], "rate": str(offer["rate"]["total"])}
    last = "нет ответа"
    for attempt in range(cfg["attempts"]):
        try:
            opened = await client.post(url, json=body, headers={"Idempotency-Key": str(app["id"])}, timeout=cfg["timeout_s"])
            if opened.status_code < 300:
                loan_id = opened.json()["loanId"]
                done = await client.post(f"{url}/{loan_id}/disburse", headers={"Idempotency-Key": f"{app['id']}:disburse"},
                                         timeout=cfg["timeout_s"])
                if done.status_code < 300:
                    result = done.json()
                    return {"loan_id": loan_id, "status": result["status"], "disbursed_at": result.get("disbursedAt"),
                            "amount": offer["amount"], "term_months": offer["term_months"], "rate": offer["rate"]["total"]}
                last = f"HTTP {done.status_code}"
            else:
                last = f"HTTP {opened.status_code}"
        except (httpx.TransportError, ValueError, KeyError) as exc:
            last = type(exc).__name__
        await asyncio.sleep(0.2 * 2 ** attempt)
    raise AbsUnavailable(f"АБС: {last}")


async def recheck(conn, inn: str, reason: str | None = None) -> list:
    """Изменились данные реестра → оферты и подписи этой компании пересматриваются (RECHECK, docs/07 N17).
    Подписи до пересмотра снимаются: подписывать будет тот, кто вправе по свежему реестру (R12)."""
    moved = []
    for app in await store.applications(conn, inn):
        if app["status"] in ("OFFERED", "SIGNING"):
            async with conn.transaction():
                app = await move(conn, app, "CHECKING", "system", flags=sorted({*app["flags"], "RECHECK"}),
                                 patch={"signatures": [], "signers": None},
                                 reason=reason or "новые данные реестра — пересмотр")
                await store.enqueue(conn, "decide", application_id=app["id"])
            moved.append(app["id"])
    return moved


async def bki_followup(conn, client: httpx.AsyncClient, app: dict) -> None:
    """Предварительная оферта (N1): КИ пришла → те же условия — флаг снимаем, другие — пересмотр с новым решением."""
    if app["status"] not in ("OFFERED", "SIGNING") or "PROVISIONAL" not in app["flags"]:
        return
    fetched = await sources.refresh(conn, client, app["company_inn"], with_bki=True, only=("bki",))
    if fetched.get("bki") != "ok":
        return
    facts, _ = await company.facts(conn, app["company_inn"])
    fresh = plain(engine.decide(facts, app["data"]["request"], load_policy(), mode="commit"))   # как лежит в JSONB
    current = app["data"].get("offer") or (app["data"].get("decision") or {}).get("offer") or {}
    same = fresh["offer"] and all(fresh["offer"][k] == current.get(k) for k in ("product", "amount", "term_months")) \
        and fresh["offer"]["rate"]["total"] == (current.get("rate") or {}).get("total")
    if same and fresh["outcome"] in ("APPROVE", "COUNTER_OFFER", "APPROVE_WITH_CONDITIONS"):
        await store.patch(conn, app, "worker", "provisional.confirmed", {"bki": "ok"},
                          flags=[f for f in app["flags"] if f != "PROVISIONAL"])
        return
    await recheck(conn, app["company_inn"])


async def sweep(conn) -> int:
    """Сроки по часам симулятора: истёкшая оферта, подпись, дозапрос, забытый черновик; просроченный SLA — флаг."""
    now, changed = await clock.now(conn), 0
    for app in await store.with_deadlines(conn):
        deadline = app["data"].get("deadline")
        if deadline and deadline["status"] == app["status"] and datetime.fromisoformat(deadline["at"]) <= now:
            await move(conn, app, deadline["then"], "timer", reason=f"истёк срок статуса {app['status']}")
            changed += 1
        elif app["status"] == "UNDER_REVIEW" and "SLA_BREACH" not in app["flags"] and app["data"].get("sla_until") \
                and datetime.fromisoformat(app["data"]["sla_until"]) <= now:
            await store.patch(conn, app, "timer", "application.flagged", {"flag": "SLA_BREACH"},
                              flags=[*app["flags"], "SLA_BREACH"])
            changed += 1
        elif app["status"] in ("OFFERED", "SIGNING") and "PROVISIONAL" in app["flags"] \
                and not await store.pending(conn, "bki_followup", app["id"]):   # одна догоняющая проверка за раз
            await store.enqueue(conn, "bki_followup", application_id=app["id"], delay_s=15 if settings.demo_mode else 300)
    return changed
