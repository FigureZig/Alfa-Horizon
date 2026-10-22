"""Флаги конструктора своей компании (seed/persona_flags.yaml): каталог и применение к описанию компании."""

from functools import cache
from pathlib import Path

import yaml

FILE = Path(__file__).with_name("persona_flags.yaml")


@cache
def catalog() -> dict:
    return yaml.safe_load(FILE.read_text("utf-8"))


def unknown(names: list[str]) -> list[str]:
    return [n for n in names if n not in catalog()["flags"]]


def not_applicable(form: str, names: list[str]) -> list[str]:
    return [n for n in names if form not in catalog()["flags"][n]["forms"]]


def apply(spec: dict, names: list[str]) -> tuple[dict, list[dict]]:
    """→ (описание компании: параметры флагов поверх полей, отказы источников для пользователя)."""
    out, faults = {**spec, "flags": list(spec.get("flags", []))}, []
    for name in names:
        flag = catalog()["flags"][name]
        out.update(flag.get("spec", {}))
        out["flags"] = sorted({*out["flags"], *flag.get("flags", [])})
        faults += [f for f in flag.get("faults", []) if f not in faults]
    return out, faults
