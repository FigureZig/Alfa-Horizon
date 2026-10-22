"""Границы модулей (docs/06 §2, docs/03 E) — по импортам в исходниках, без внешних инструментов.

Домен — чистые функции без ввода-вывода; ядро решения не зависит от умного слоя K1–K5 (его можно выключить флагом,
основа останется); HTTP-фреймворк знают только API и точка входа.
"""

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
IO_PACKAGES = {"asyncpg", "httpx", "fastapi", "starlette", "yaml"}
IO_MODULES = ("app.store", "app.sources", "app.api", "app.lifecycle", "app.worker", "app.company", "app.personas", "app.clock")
CORE = ("engine", "scoring", "catalog", "calc", "state", "rights", "okved")
SMART = {"app.domain.forecast", "app.domain.levers", "app.domain.repayment"}      # K1, K3, K4


def imports(path: Path) -> set[str]:
    package = ".".join(path.relative_to(APP.parent).with_suffix("").parts[:-1])
    out = set()
    for node in ast.walk(ast.parse(path.read_text("utf-8"))):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            base = package.split(".")[: len(package.split(".")) - node.level + 1] if node.level else []
            module = ".".join([*base, node.module] if node.module else base)
            out |= {module} | {f"{module}.{a.name}" for a in node.names}
    return out


def test_domain_is_pure_functions_without_io():
    for path in (APP / "domain").glob("*.py"):
        found = imports(path)
        bad = {m for m in found if m.split(".")[0] in IO_PACKAGES or m.startswith(IO_MODULES)}
        assert not bad, (path.name, bad)


def test_decision_core_does_not_depend_on_the_smart_layer():
    for name in CORE:
        assert not imports(APP / "domain" / f"{name}.py") & SMART, name


def test_only_api_and_entrypoint_know_the_http_framework():
    for path in APP.rglob("*.py"):
        if any(m.split(".")[0] in ("fastapi", "starlette") for m in imports(path)):
            assert path.parent.name == "api" or path.name == "main.py", path
