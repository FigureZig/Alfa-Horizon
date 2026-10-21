"""Настройки из окружения. Значения по умолчанию — для локального запуска вне Docker (порты из docker-compose.yml)."""

import os
from dataclasses import dataclass, field
from datetime import date


def _flag(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "postgresql://app:app@localhost:55432/credit")
    wiremock_url: str = os.getenv("WIREMOCK_URL", "http://localhost:8081")
    demo_mode: bool = _flag("DEMO_MODE", True)
    # Демо-мир построен на 21.10.2026: часы песочницы по умолчанию стоят на этой дате (docs/08 §5).
    demo_today: str = os.getenv("DEMO_TODAY", "2026-10-21")
    features: frozenset[str] = field(default_factory=lambda: frozenset(
        k for k, default in (("K1", True), ("K2", True), ("K3", True), ("K4", False), ("K5", False))
        if _flag(f"FEATURE_{k}", default)))


settings = Settings()


def today() -> date:
    return date.fromisoformat(settings.demo_today) if settings.demo_mode else date.today()
