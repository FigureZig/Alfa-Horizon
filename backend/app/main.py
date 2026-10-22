"""API: uvicorn app.main:app. Документация — Swagger /api/docs и ReDoc /api/redoc, контракт — /api/openapi.json.

Ответ — {"data": …}, ошибка — RFC 9457 с машинным кодом (app/api/http.py); у каждого ответа X-Request-Id.
CORS — для фронта на другом порту (CORS_ORIGINS).
"""

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import RedirectResponse
from starlette.exceptions import HTTPException

from . import store
from .api import bank, cabinet, client, docs, sandbox
from .api.http import Problem, problem
from .config import settings
from .domain.state import TransitionError

log = logging.getLogger("api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await store.close()


app = FastAPI(title="Alfa Horizon — умный кредитный кабинет", version="0.3.0", lifespan=lifespan,
              summary="Кредитный конвейер для малого бизнеса: кабинет предпринимателя и рабочее место банка",
              description=docs.DESCRIPTION, openapi_tags=docs.TAGS, swagger_ui_parameters=docs.SWAGGER,
              docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Request-Id"])
app.include_router(client.router, prefix="/api/v1")
app.include_router(cabinet.router, prefix="/api/v1")
app.include_router(bank.router, prefix="/api/v1")
if settings.demo_mode:                       # в бою симулятора нет вообще (docs/08 §9)
    app.include_router(sandbox.auth_router, prefix="/api/v1")
    app.include_router(sandbox.router, prefix="/api/v1")


def openapi() -> dict:
    """Контракт с ошибками RFC 9457 и группами разделов для ReDoc (app/api/docs.py)."""
    if not app.openapi_schema:
        app.openapi_schema = docs.customize(get_openapi(
            title=app.title, version=app.version, summary=app.summary, description=app.description, routes=app.routes,
            tags=app.openapi_tags))
    return app.openapi_schema


app.openapi = openapi


@app.get("/docs", include_in_schema=False)
async def docs_alias():
    return RedirectResponse("/api/docs")


@app.get("/redoc", include_in_schema=False)
async def redoc_alias():
    return RedirectResponse("/api/redoc")


@app.middleware("http")
async def request_id(request: Request, call_next):
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex
    response = await call_next(request)
    response.headers["X-Request-Id"] = rid
    return response


@app.exception_handler(Problem)
async def on_problem(_: Request, exc: Problem):
    return problem(exc.status, exc.code, exc.detail, **exc.extra)


@app.exception_handler(TransitionError)
async def on_transition(_: Request, exc: TransitionError):
    return problem(409, "INVALID_TRANSITION", str(exc))


@app.exception_handler(RequestValidationError)
async def on_validation(_: Request, exc: RequestValidationError):
    errors = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return problem(422, "VALIDATION_ERROR", "проверьте поля запроса", errors=errors)


@app.exception_handler(HTTPException)
async def on_http(_: Request, exc: HTTPException):
    code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
    return problem(exc.status_code, code, str(exc.detail))


@app.exception_handler(Exception)
async def on_error(request: Request, exc: Exception):
    log.exception("unhandled %s %s", request.method, request.url.path)
    return problem(500, "INTERNAL_ERROR", "внутренняя ошибка — мы уже разбираемся")
