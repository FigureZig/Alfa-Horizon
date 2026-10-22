"""Ошибка команды с машинным кодом для фронта; API отдаёт её как RFC 9457 (app/api/http.py)."""


class Problem(Exception):
    """raise Problem(404, "APPLICATION_NOT_FOUND", "заявка не найдена", id=...)."""

    RESERVED = frozenset({"type", "title", "status", "detail", "code"})   # поля RFC 9457 — их не перекрыть

    def __init__(self, status: int, code: str, detail: str, **extra):
        clash = self.RESERVED & extra.keys()
        if clash:
            raise ValueError(f"поля {sorted(clash)} зарезервированы RFC 9457")
        super().__init__(detail)
        self.status, self.code, self.detail, self.extra = status, code, detail, extra
