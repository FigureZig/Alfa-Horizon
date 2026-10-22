"""Модель данных: uv run python -m qa.er → docs/diagrams/data_model.md

Физическая модель — из SQL-миграций (migrations/*.sql), логическая — документ заявки в applications.data — из моделей
ответов API (app/api/schemas.py: ApplicationView и вложенные). Руками файл не правят; тест сверяет его с кодом.
"""

import re
import types
import typing
from pathlib import Path

from pydantic import BaseModel

from app.api import schemas

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "docs" / "diagrams" / "data_model.md"
TABLE = re.compile(r"CREATE TABLE (\w+) \((.*?)\n\);", re.S)
COLUMN = re.compile(r"^\s+(\w+)\s+([\w\[\]]+)(.*?)(?:--\s*(.*))?$")
REFERENCES = re.compile(r"REFERENCES (\w+) \((\w+)\)")
ABOUT = {"applications": "заявка целиком", "events": "история и аудит, только добавление",
         "jobs": "очередь задач worker и таймеры", "snapshots": "ответы реестров и банка с происхождением",
         "kv": "операционные мелочи"}


def tables() -> list[dict]:
    sql = "\n".join(p.read_text("utf-8") for p in sorted((ROOT / "migrations").glob("*.sql")))
    out = []
    for name, body in TABLE.findall(sql):
        columns, pk = [], []
        for line in body.splitlines():
            if m := re.match(r"\s+PRIMARY KEY \((.+)\)", line):
                pk = [c.strip() for c in m.group(1).split(",")]
                continue
            if not (m := COLUMN.match(line)) or m.group(1).upper() in ("PRIMARY", "UNIQUE", "CONSTRAINT"):
                continue
            col, kind, rest, comment = m.groups()
            ref = REFERENCES.search(rest)
            columns.append({"name": col, "type": kind.replace("[]", "_array"), "pk": "PRIMARY KEY" in rest,
                            "fk": ref.groups() if ref else None, "unique": "UNIQUE" in rest,
                            "comment": (comment or "").strip().rstrip(",")})
        for c in columns:
            c["pk"] = c["pk"] or c["name"] in pk
        out.append({"name": name, "columns": columns})
    return out


def _keys(c: dict) -> str:
    keys = [k for k, on in (("PK", c["pk"]), ("FK", c["fk"]), ("UK", c["unique"])) if on]
    return f" {','.join(keys)}" if keys else ""


def physical() -> list[str]:
    lines = ["erDiagram"]
    for t in tables():
        for c in t["columns"]:
            if c["fk"]:
                lines.append(f'    {c["fk"][0]} |o--o{{ {t["name"]} : "{c["name"]}"')
    for t in tables():
        lines.append(f"    {t['name']} {{")
        for c in t["columns"]:
            note = f' "{c["comment"]}"' if c["comment"] else ""
            lines.append(f"        {c['type']} {c['name']}{_keys(c)}{note}")
        lines.append("    }")
    return lines


def _nested(annotation) -> tuple[type[BaseModel] | None, bool, bool]:
    """→ (вложенная модель, список ли, может ли отсутствовать)."""
    many = optional = False
    for _ in range(3):
        origin, args = typing.get_origin(annotation), typing.get_args(annotation)
        if origin in (typing.Union, types.UnionType):
            optional = optional or type(None) in args
            annotation = next(a for a in args if a is not type(None))
        elif origin is list:
            many, annotation = True, args[0]
        else:
            break
    model = annotation if isinstance(annotation, type) and issubclass(annotation, BaseModel) else None
    return model, many, optional


def _kind(annotation) -> str:
    args = [a for a in typing.get_args(annotation) if a is not type(None)]
    if typing.get_origin(annotation) in (typing.Union, types.UnionType) and len(args) == 1:
        annotation = args[0]                                   # X | None → X
    origin = typing.get_origin(annotation)
    if origin is list:
        return "list"
    if origin is dict:
        return "json"
    if origin is typing.Literal:
        return "enum"
    return {str: "str", int: "int", float: "float", bool: "bool"}.get(annotation, "any")


def logical() -> list[str]:
    lines, seen, queue = ["erDiagram"], set(), [schemas.ApplicationView]
    entities = []
    while queue:
        model = queue.pop(0)
        if model.__name__ in seen:
            continue
        seen.add(model.__name__)
        attrs = []
        for name, field in model.model_fields.items():
            nested, many, optional = _nested(field.annotation)
            if nested is not None:
                mark = "o{" if many else "o|" if optional else "||"
                lines.append(f'    {model.__name__} ||--{mark} {nested.__name__} : "{field.alias or name}"')
                queue.append(nested)
            else:
                attrs.append(f"        {_kind(field.annotation)} {field.alias or name}")
        entities.append((model.__name__, attrs))
    for name, attrs in entities:
        lines += [f"    {name} {{", *attrs, "    }"]
    return lines


def render() -> str:
    return "\n".join([
        "# Модель данных",
        "",
        "Сгенерировано из кода: `cd backend && uv run python -m qa.er`. Физическая модель — из `backend/migrations/*.sql`, "
        "логическая — из схем ответов API `backend/app/api/schemas.py`. Почему так мало таблиц — `06_architecture.md` §4.",
        "",
        "## 1. Таблицы PostgreSQL",
        "",
        *[f"- `{t['name']}` — {ABOUT.get(t['name'], '')}" for t in tables()],
        "",
        "Компания и человек — не таблицы: их данные приходят из реестров и банка и лежат в `snapshots` (ключ — ИНН), права "
        "считаются на лету. Продукты, правила и скоринг — `policy/*.yaml`, версия политики пишется в каждое решение.",
        "",
        "```mermaid",
        *physical(),
        "```",
        "",
        "## 2. Заявка как документ (`applications.data`)",
        "",
        "Запрос, решение движка с причинами и скорингом, оферта и варианты, подписи, согласие участников, решения банка и выдача "
        "хранятся одним документом заявки: читаются вместе, меняются в одной транзакции с событием в `events`. "
        "Те же поля отдаёт `GET /api/v1/applications/{id}` (схема `ApplicationView` в Swagger и ReDoc).",
        "",
        "```mermaid",
        *logical(),
        "```",
        "",
    ])


def main() -> None:
    OUT.write_text(render(), "utf-8")
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
