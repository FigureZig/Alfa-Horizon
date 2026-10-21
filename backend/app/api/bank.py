"""Сторона банка (Must по ответам организаторов 21.10): очередь исключений и досье заявки."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from .. import company, store
from ..jsonutil import plain

router = APIRouter(prefix="/bank", tags=["bank"])


@router.get("/queue")
async def queue():
    """Только исключения: заявки у специалиста с причиной и предложением движка."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        rows = await store.queue(conn)
    items = []
    for app in rows:
        decision = app["data"].get("decision") or {}
        items.append({"id": app["id"], "inn": app["company_inn"], "status": app["status"], "flags": app["flags"],
                      "request": decision.get("request") or app["data"].get("request"),
                      "reasons": [r for r in decision.get("reasons", []) if r["kind"] == "manual"],
                      "proposal": decision.get("offer"), "updatedAt": app["updated_at"]})
    return plain({"items": items})


@router.get("/applications/{app_id}/dossier")
async def dossier(app_id: UUID):
    """Всё на одном экране: факты с источниками, скоринг с вкладами, правила с нормами, история."""
    pool = await store.pool()
    async with pool.acquire() as conn:
        app = await store.get_application(conn, app_id)
        if app is None:
            raise HTTPException(404, "заявка не найдена")
        facts, provenance = await company.facts(conn, app["company_inn"])
        history = await store.events(conn, app_id)
    return plain({"application": app, "facts": facts, "sources": provenance, "events": history})
