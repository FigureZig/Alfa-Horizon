"""Сторона банка (Must по ответам организаторов 21.10): очередь исключений, досье заявки и решение специалиста."""

from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from .. import company, lifecycle, store
from . import schemas as S
from . import views
from .deps import Me, require_bank
from .http import ok
from .schemas import doc

router = APIRouter(prefix="/bank", tags=["bank"])


@router.get("/queue", **doc(S.QueueResponse, 401, 403, summary="Очередь заявок на рассмотрении"))
async def queue(who: Me):
    """Только исключения: заявки у специалиста с причиной, предложением движка и сроком SLA."""
    require_bank(who)
    pool = await store.pool()
    async with pool.acquire() as conn:
        rows = await store.queue(conn)
    items = []
    for app in rows:
        decision = app["data"].get("decision") or {}
        items.append({"id": app["id"], "inn": app["company_inn"], "status": app["status"], "flags": app["flags"],
                      "request": decision.get("request") or app["data"].get("request"),
                      "reasons": [r for r in decision.get("reasons", []) if r["kind"] == "manual"],
                      "proposal": decision.get("offer"), "risk": decision.get("risk"),
                      "pending_decision": app["data"].get("pending_decision"),
                      "available_actions": lifecycle.actions(app, role=who.role),
                      "sla_until": app["data"].get("sla_until"), "updated_at": app["updated_at"]})
    return ok(items)


FIRST_DECISION = {"OFFERED", "REJECTED", "INFO_REQUESTED", "UNDER_REVIEW"}
TARGET_DECISION_S = 60                            # авторешение P95 ≤ 60 с (docs/07 §8)


def _percentiles(values: list[float], target: float | None) -> dict:
    if not values:
        return {"count": 0, "p50": None, "p95": None, "target": target, "within_target": None}
    ordered = sorted(values)

    def pick(q: float) -> float:
        return round(ordered[min(len(ordered) - 1, int(q * len(ordered)))], 3)

    share = round(sum(v <= target for v in ordered) / len(ordered), 3) if target else None
    return {"count": len(ordered), "p50": pick(0.5), "p95": pick(0.95), "target": target, "within_target": share}


@router.get("/metrics", **doc(S.BankMetricsResponse, 401, 403, summary="Метрики конвейера: STP, время решения, SLA"))
async def metrics(who: Me):
    """Сквозная обработка и сроки по истории событий: сколько решений принято без специалиста (STP), время от подачи
    до решения и ручного рассмотрения против целей docs/07 §8, исходы движка, выдачи и просрочки SLA."""
    require_bank(who)
    pool = await store.pool()
    async with pool.acquire() as conn:
        apps = await conn.fetch("SELECT id, status, flags, data FROM applications")
        rows = await conn.fetch("""SELECT application_id, at, type, payload FROM events
                                   WHERE type IN ('application.status_changed', 'decision.made') ORDER BY id""")
    submitted, decided, queued, manual, outcomes = {}, [], {}, [], {}
    for r in rows:
        app_id, payload = r["application_id"], r["payload"]
        if r["type"] == "decision.made":
            outcomes[payload["outcome"]] = outcomes.get(payload["outcome"], 0) + 1
            continue
        to = payload.get("to")
        if to == "SUBMITTED":
            submitted[app_id] = r["at"]
        elif to in FIRST_DECISION and app_id in submitted:
            decided.append((app_id, to, (r["at"] - submitted.pop(app_id)).total_seconds()))
        if to == "UNDER_REVIEW":
            queued[app_id] = r["at"]
        elif app_id in queued and to not in ("UNDER_REVIEW",):
            manual.append((r["at"] - queued.pop(app_id)).total_seconds())
    auto = sum(1 for _, to, _ in decided if to != "UNDER_REVIEW")
    by_status: dict[str, int] = {}
    for app in apps:
        by_status[app["status"]] = by_status.get(app["status"], 0) + 1
    loans = [a["data"]["loan"] for a in apps if a["status"] == "ISSUED" and a["data"].get("loan")]
    return ok({
        "applications": len(apps), "by_status": by_status,
        "decisions": {"auto": auto, "manual": len(decided) - auto,
                      "stp_share": round(auto / len(decided), 3) if decided else None},
        "time_to_decision": _percentiles([t for _, to, t in decided if to != "UNDER_REVIEW"], TARGET_DECISION_S),
        "manual_review": _percentiles(manual, lifecycle.timer_s("manual_sla")),
        "outcomes": outcomes,
        "issued": {"count": len(loans), "amount": str(sum((Decimal(str(loan["amount"])) for loan in loans), Decimal(0)))},
        "sla_breaches": sum("SLA_BREACH" in a["flags"] for a in apps),
    })


@router.get("/audit", **doc(S.AuditCheckResponse, 401, 403, summary="Проверка журнала аудита: цепочка хэшей цела"))
async def audit(who: Me):
    """Журнал событий только дописывается, каждая запись содержит хэш предыдущей (docs/10 P19). Ручка пересчитывает цепочку
    с первой записи и показывает, цела ли она, а если нет — с какой записи журнал правили."""
    require_bank(who)
    pool = await store.pool()
    async with pool.acquire() as conn:
        return ok(await store.verify_chain(conn))


@router.get("/applications/{app_id}/dossier",
            **doc(S.DossierResponse, 401, 403, 404, summary="Досье: факты, источники и история заявки"))
async def dossier(app_id: UUID, who: Me):
    """Всё на одном экране: заявка, факты с источниками, скоринг с вкладами, правила с нормами, история."""
    require_bank(who)
    pool = await store.pool()
    async with pool.acquire() as conn:
        app = await lifecycle.load(conn, app_id)
        facts, provenance = await company.facts(conn, app["company_inn"])
        history = await store.events(conn, app_id)
    return ok({"application": views.application(app, role=who.role), "facts": facts, "sources": provenance, "events": history})


class ConfirmIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [
        {"approve": True, "comment": "Подтверждаю: досье полное, залог достаточный"}]})
    approve: bool = Field(description="true — подтвердить одобрение специалиста, false — вернуть ему")
    comment: str | None = Field(None, max_length=2000)


class DecisionIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [
        {"action": "approve", "amount": 12000000, "term_months": 24, "comment": "Одобряю по досье: обороты стабильные"}]})
    action: Literal["approve", "reject", "request_info"]
    amount: Decimal | None = Field(None, gt=0, description="одобрить другую сумму; цена — та же цена риска")
    term_months: int | None = Field(None, gt=0, le=120)
    comment: str | None = Field(None, max_length=2000)
    asks: list[str] | None = Field(None, description="что запросить у клиента (для request_info)")


@router.post("/applications/{app_id}/decision",
             **doc(S.ApplicationResponse, 401, 403, 404, 409, 422,
                   summary="Решение специалиста: одобрить, отказать, дозапросить"))
async def decide(app_id: UUID, body: DecisionIn, who: Me):
    """Решение специалиста по заявке на ручном рассмотрении: одобрить, отказать или дозапросить документы."""
    require_bank(who)
    pool = await store.pool()
    async with pool.acquire() as conn:
        app = await lifecycle.load(conn, app_id)
        app = await lifecycle.bank_decide(conn, app, who.label, body.action, amount=body.amount, term_months=body.term_months,
                                          comment=body.comment, asks=body.asks, role=who.role)
    return ok(views.application(app, role=who.role))


@router.post("/applications/{app_id}/decision/confirm",
             **doc(S.ApplicationResponse, 401, 403, 404, 409, summary="Второй ключ риск-менеджера"))
async def confirm(app_id: UUID, body: ConfirmIn, who: Me):
    """Второй ключ: риск-менеджер подтверждает одобрение специалиста выше его порога или возвращает его."""
    require_bank(who, "risk_manager")
    pool = await store.pool()
    async with pool.acquire() as conn:
        app = await lifecycle.load(conn, app_id)
        app = await lifecycle.confirm(conn, app, who.label, body.approve, body.comment)
    return ok(views.application(app, role=who.role))
