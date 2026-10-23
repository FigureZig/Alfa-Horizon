"""Кто делает запрос и что ему можно (docs/06 §10). JWT пользователя → человек → права из снапшотов на каждый запрос.

Без токена в режиме симулятора запрос идёт от активного пользователя (последний вход, по умолчанию — DEFAULT_PERSONA):
так работают curl-примеры и страницы фронта до подключения входа. В бою без токена — 401.
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .. import auth, company, personas, store
from ..config import settings
from ..domain.rights import rights
from .http import Problem

BANK_RIGHTS = {"roles": [{"role": "bank_officer"}], "can": {"view": True, "prepare": False, "sign": False, "approve": False},
               "sign_mode": None, "why": []}
NO_RIGHT = {"view": "кабинет и счёт компании видят руководитель и те, кому компания дала доступ в интернет-банк; участник "
                    "общества голосует по крупной сделке в самой заявке",
            "prepare": "готовить и подавать заявки может руководитель или пользователь ДБО с правом подготовки",
            "sign": "подписывать может руководитель без блокировок или ИП",
            "approve": "голосовать за крупную сделку могут участники ООО"}


@dataclass(frozen=True)
class Actor:
    persona_id: str
    kind: str                  # client · bank
    inn: str | None            # ИНН человека-клиента
    name: str
    role: str = "client"       # client · loan_officer · risk_manager

    @property
    def label(self) -> str:    # кто в событиях аудита
        return f"{self.kind}:{self.inn or self.persona_id}"


def actor_of(persona: dict) -> Actor:
    if persona["kind"] == "bank":
        last, first = persona["staff"]["fio"][:2]
        return Actor(persona["id"], "bank", None, f"{first} {last}", persona["staff"]["role"])
    person = persona["person"]
    return Actor(persona["id"], "client", person["inn"], " ".join(person["fio"]))


def _linked(persona: dict, inn: str) -> bool:
    return persona["kind"] == "bank" or any(c["inn"] == inn for c in persona.get("companies", []))


bearer = HTTPBearer(auto_error=False, scheme_name="JWT", bearerFormat="JWT",
                    description="`data.token` из `POST /api/v1/auth/login` или `POST /api/v1/sandbox/personas/{id}/login`")


async def current_actor(request: Request,
                        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)] = None) -> Actor:
    """Токен → его пользователь. Без токена в симуляторе: кабинет компании открывает её пользователь (вход по ИНН, как
    у фронта), остальное — последний вошедший."""
    token = credentials.credentials.strip() if credentials else None
    pool = await store.pool()
    async with pool.acquire() as conn:
        if token:
            claims = auth.verify(token)
            if claims is None:
                raise Problem(401, "TOKEN_INVALID", "токен не подошёл или истёк — войдите заново")
            persona = await personas.get(conn, claims["sub"])
        elif settings.demo_mode:
            persona = await personas.get(conn, await personas.active_id(conn))
            inn = request.path_params.get("inn") or request.query_params.get("company_inn")
            if inn and not (persona and _linked(persona, inn)):
                persona = await personas.for_company(conn, inn) or persona
        else:
            raise Problem(401, "LOGIN_REQUIRED", "нужен вход")
    if persona is None:
        raise Problem(401, "USER_UNKNOWN", "такого пользователя больше нет — войдите заново")
    return actor_of(persona)


Me = Annotated[Actor, Depends(current_actor)]


async def access(conn, who: Actor, inn: str) -> tuple[dict, dict, list[dict]]:
    """→ (права, факты, происхождение). Данных о компании ещё нет — 409, их собирает worker."""
    facts, provenance = await company.facts(conn, inn)
    if not provenance:
        raise Problem(409, "COMPANY_NOT_LOADED", "данных о компании ещё нет — банк их собирает", inn=inn)
    return (BANK_RIGHTS if who.kind == "bank" else rights(who.inn, facts)), facts, provenance


async def require(conn, who: Actor, inn: str, right: str) -> tuple[dict, dict]:
    granted, facts, _ = await access(conn, who, inn)
    if not granted["can"][right]:
        raise Problem(403, "FORBIDDEN", NO_RIGHT[right], right=right, roles=granted["roles"], why=granted["why"])
    return granted, facts


def voter(app: dict, who: Actor, granted: dict) -> bool:
    """Участник, которого заявка просит проголосовать за крупную сделку: эту заявку он видит и без доступа к счёту."""
    approval = app["data"].get("approval") or {}
    return bool(granted["can"].get("approve")) and who.inn in {p["inn"] for p in approval.get("participants", [])}


def require_feature(code: str) -> None:
    """Умная функция за флагом FEATURE_<code> (docs/03): выключена — ручки нет, основа работает без неё."""
    if code not in settings.features:
        raise Problem(404, "FEATURE_OFF", f"функция {code} выключена (FEATURE_{code}=false)", feature=code)


def feature(code: str):
    """Зависимость маршрута: флаг проверяется раньше входа и чтения данных — выключенная функция их не трогает."""
    def check() -> None:
        require_feature(code)
    return Depends(check)


def require_bank(who: Actor, role: str | None = None) -> None:
    if who.kind != "bank":
        raise Problem(403, "BANK_ONLY", "это действие сотрудника банка — войдите как кредитный специалист")
    if role and who.role != role:
        raise Problem(403, "ROLE_REQUIRED", "это действие риск-менеджера" if role == "risk_manager"
                      else "это действие кредитного специалиста", role=role)
