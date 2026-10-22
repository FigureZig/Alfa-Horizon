"""Факты о компании из снапшотов: что банк знает, откуда и насколько свежо (общий код для API и worker)."""

from . import clock, store
from .features import company_facts
from .policy import sources as source_config


async def facts(conn, inn: str) -> tuple[dict, list[dict]]:
    """→ (факты, происхождение). Упавший источник — последний удачный ответ с флагом DEGRADED_DATA (STALE_OK);
    у источников с TTL 0 (БКИ) старый ответ не используем — только свежий для этой заявки."""
    company_sources = {name: s for name, s in source_config()["sources"].items() if s.get("scope", "company") == "company"}
    ttl = {name: s.get("ttl_h", 1) for name, s in company_sources.items()}
    snaps = {name: snap for name, snap in (await store.snapshots(conn, inn)).items() if name in company_sources}
    payloads, provenance = {}, []
    for name, snap in sorted(snaps.items()):
        stale = snap["error"] is not None
        usable = snap["payload"] is not None and not (stale and ttl.get(name, 1) == 0)
        if usable:
            payloads[name] = snap["payload"]
        provenance.append({"source": name, "status": snap["status"], "fetched_at": snap["fetched_at"],
                           "error": snap["error"], "used": usable, "stale": stale and usable})
    result = company_facts(inn, payloads, await clock.today(conn))
    result["degraded"] = [p["source"] for p in provenance if p["stale"]]
    return result, provenance
