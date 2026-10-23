"""Факты о компании из снапшотов: что банк знает, откуда и насколько свежо (общий код для API и worker)."""

from decimal import Decimal

from . import clock, store
from .features import company_facts
from .policy import sources as source_config

FORGOTTEN_KEY = "sandbox:forgotten_loans"   # id заявок, выданных до сброса мира симулятора


async def facts(conn, inn: str) -> tuple[dict, list[dict]]:
    """→ (факты, происхождение). Упавший источник — последний удачный ответ с флагом DEGRADED_DATA (STALE_OK);
    у источников с TTL 0 (БКИ) старый ответ не используем — только свежий для этой заявки."""
    company_sources = {name: s for name, s in source_config()["sources"].items() if s.get("scope", "company") == "company"}
    ttl = {name: s.get("ttl_h", 1) for name, s in company_sources.items()}
    snaps = {name: snap for name, snap in (await store.snapshots(conn, inn)).items() if name in company_sources}
    payloads, provenance, shift = {}, [], await clock.shift(conn)
    for name, snap in sorted(snaps.items()):
        stale = snap["error"] is not None
        usable = snap["payload"] is not None and not (stale and ttl.get(name, 1) == 0)
        if usable:
            payloads[name] = snap["payload"]
        provenance.append({"source": name, "status": snap["status"],          # когда получено — по часам мира
                           "fetched_at": snap["fetched_at"] + shift if snap["fetched_at"] else None,
                           "error": snap["error"], "used": usable, "stale": stale and usable})
    result = company_facts(inn, payloads, await clock.today(conn))
    result["degraded"] = [p["source"] for p in provenance if p["stale"]]
    _with_own_loans(result, await own_loans(conn, inn))
    return result, provenance


async def own_loans(conn, inn: str) -> list[dict]:
    """Кредиты, которые выдал сам банк: о них он знает сразу, а в выписке и кредитной истории их ещё нет.
    Выданные до сброса мира симулятора (`POST /sandbox/reset`) не считаются: история заявок остаётся, мир — как сначала.
    Помним их по id, а не по времени: сброс возвращает часы назад, и выданное после перемотки оказалось бы «позже» сброса."""
    out, forgotten = [], set(await store.kv_get(conn, FORGOTTEN_KEY, []))
    for app in await store.applications(conn, inn):
        loan, offer = app["data"].get("loan"), app["data"].get("offer")
        if app["status"] != "ISSUED" or not loan or not offer or str(app["id"]) in forgotten:
            continue
        out.append({"application_id": str(app["id"]), "number": loan.get("number"), "product": offer["product"],
                    "repayment": offer["repayment"], "amount": Decimal(str(offer["amount"])),
                    "rate": Decimal(str(offer["rate"]["total"])), "term_months": offer["term_months"],
                    "payment": Decimal(str(offer["payment"])), "disbursed_at": loan.get("disbursed_at")})
    return out


def _with_own_loans(facts: dict, loans: list[dict]) -> None:
    """Свои кредиты — в факты: платежи по ним входят в нагрузку и лимиты, подключённый овердрафт второй раз не
    предлагаем, а его лимит прикрывает минус в прогнозе остатка (K1)."""
    if not loans:
        return
    term = [loan for loan in loans if loan["repayment"] != "revolving"]
    facts["own_loans"] = loans
    facts["own_payments"] = sum((loan["payment"] for loan in term), Decimal(0))
    facts["held_products"] = sorted({loan["product"] for loan in loans})
    facts["credit_line"] = sum((loan["amount"] for loan in loans if loan["repayment"] == "revolving"), Decimal(0)) or None
    if facts.get("debt_payments") is not None and facts.get("inflow_avg"):
        facts["debt_load"] = round(float((facts["debt_payments"] + facts["own_payments"]) / facts["inflow_avg"]), 4)


async def forget_loans(conn) -> None:
    """Сброс мира: всё, что выдано к этому моменту, остаётся в истории заявок, но в фактах компаний больше не участвует."""
    await store.kv_set(conn, FORGOTTEN_KEY, await store.application_ids(conn, "ISSUED"))
