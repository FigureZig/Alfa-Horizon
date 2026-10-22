"""Настройки из окружения. Значения по умолчанию — для локального запуска вне Docker (порты из docker-compose.yml)."""

import os
from dataclasses import dataclass, field

DEV_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://localhost:8080"


def _flag(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "postgresql://app:app@localhost:55432/credit")
    wiremock_url: str = os.getenv("WIREMOCK_URL", "http://localhost:8081")
    demo_mode: bool = _flag("DEMO_MODE", True)
    # Мир симулятора построен на 21.10.2026: его часы по умолчанию стоят на этой дате (docs/08 §5).
    demo_today: str = os.getenv("DEMO_TODAY", "2026-10-21")
    # Вход пользователем симулятора (docs/06 §10): подпись токена. В бою — секрет из окружения, не из репозитория.
    token_secret: str = os.getenv("DEMO_TOKEN_SECRET", "dev-only-not-a-secret")
    # Кем считать запрос без токена в симуляторе, пока никто не вошёл: пресет из seed/personas.yaml.
    default_persona: str = os.getenv("DEFAULT_PERSONA", "s7")
    cors_origins: tuple[str, ...] = tuple(o.strip() for o in os.getenv("CORS_ORIGINS", DEV_ORIGINS).split(",") if o.strip())
    features: frozenset[str] = field(default_factory=lambda: frozenset(
        k for k, default in (("K1", True), ("K2", True), ("K3", True), ("K4", True), ("K5", True))
        if _flag(f"FEATURE_{k}", default)))


settings = Settings()
