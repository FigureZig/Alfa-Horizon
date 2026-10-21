"""API: uvicorn app.main:app. Документация — /api/docs, контракт — /api/openapi.json."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import store
from .api import bank, client, sandbox
from .config import settings
from .domain.state import TransitionError


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await store.close()


app = FastAPI(title="Умный кредитный кабинет", version="0.1.0", lifespan=lifespan,
              docs_url="/api/docs", openapi_url="/api/openapi.json")
app.include_router(client.router, prefix="/api/v1")
app.include_router(bank.router, prefix="/api/v1")
if settings.demo_mode:                       # в бою песочницы нет вообще (docs/08 §9)
    app.include_router(sandbox.router, prefix="/api/v1")


@app.exception_handler(TransitionError)
async def transition_error(_: Request, exc: TransitionError):
    """Problem Details (RFC 9457): машинный код + человеческий текст."""
    return JSONResponse(status_code=409, media_type="application/problem+json",
                        content={"type": "about:blank", "title": "Действие недоступно в текущем статусе",
                                 "status": 409, "detail": str(exc), "code": "INVALID_TRANSITION"})
