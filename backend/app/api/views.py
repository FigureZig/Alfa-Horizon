"""Ресурсы API в одном виде для клиента и банка: заявка с текущей офертой, подписями, сроком и доступными действиями."""

from .. import lifecycle


def application(app: dict, can: dict | None = None, *, role: str = "client", person_inn: str | None = None) -> dict:
    d = app["data"]
    return {
        "id": app["id"], "company_inn": app["company_inn"], "status": app["status"], "flags": app["flags"],
        "version": app["version"], "created_at": app["created_at"], "updated_at": app["updated_at"],
        "request": d.get("request"), "consent_bki": d.get("consent_bki", False), "created_by": d.get("created_by"),
        "decision": d.get("decision"),
        "offer": d.get("offer") or (d.get("decision") or {}).get("offer"),     # принятая или предложенная
        "offers": lifecycle.offers(app),                                       # основная и альтернативы для выбора
        "info_request": d.get("info_request"), "signers": d.get("signers"), "signatures": d.get("signatures", []),
        "approval": d.get("approval"), "pending_decision": d.get("pending_decision"),
        "bank_decision": d.get("bank_decision"), "loan": d.get("loan"), "final_check": d.get("final_check"),
        "deadline": d.get("deadline"), "sla_until": d.get("sla_until"),
        "available_actions": lifecycle.actions(app, can, role=role, person_inn=person_inn),
    }
