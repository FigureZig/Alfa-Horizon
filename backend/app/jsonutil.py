"""JSON без потерь: деньги — строкой (Decimal не превращается во float), даты — ISO 8601."""

import json
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


def _default(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, date | datetime):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, set | frozenset):
        return sorted(obj)
    raise TypeError(f"{type(obj).__name__} не сериализуется")


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=_default)


def plain(obj):
    """Структура только из JSON-типов — для ответов API и записи в JSONB."""
    return json.loads(dumps(obj))
