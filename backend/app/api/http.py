"""Вид ответов API (docs/06 §5): успех — {"data": …}, ошибка — RFC 9457 (application/problem+json) с машинным кодом.

Поля — snake_case, деньги — строкой (Decimal без потерь), даты — ISO 8601.
"""

from fastapi.responses import JSONResponse

from ..errors import Problem
from ..jsonutil import plain

__all__ = ["Problem", "ok", "problem"]

TITLES = {400: "Неверный запрос", 401: "Нужен вход", 403: "Недостаточно прав", 404: "Не найдено",
          405: "Метод не поддерживается", 409: "Действие недоступно в текущем состоянии", 422: "Ошибка в данных запроса",
          500: "Внутренняя ошибка", 502: "Внешняя система не ответила", 503: "Сервис временно недоступен"}


def ok(payload, **meta) -> dict:
    return {"data": plain(payload), **({"meta": plain(meta)} if meta else {})}


def problem(status: int, code: str, detail: str, **extra) -> JSONResponse:
    body = {"type": "about:blank", "title": TITLES.get(status, "Ошибка"), "status": status, "detail": detail, "code": code}
    return JSONResponse(status_code=status, media_type="application/problem+json", content=plain({**body, **extra}))
