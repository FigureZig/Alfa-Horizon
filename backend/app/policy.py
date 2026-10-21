"""Политика из YAML (policy/). Версия = version из файла политики + hash всех файлов — пишется в каждое решение."""

import hashlib
from functools import lru_cache
from pathlib import Path

import yaml

POLICY_DIR = Path(__file__).resolve().parent.parent / "policy"


def _read(path: Path) -> dict:
    return yaml.safe_load(path.read_text("utf-8"))


@lru_cache
def load(policy_dir: str | None = None) -> dict:
    root = Path(policy_dir) if policy_dir else POLICY_DIR
    policy_file = sorted(root.glob("policy-*.yaml"))[-1]          # активна последняя версия
    files = [policy_file, root / "products.yaml", root / "market.yaml"]
    pol = _read(policy_file)
    catalog = _read(root / "products.yaml")
    pol.update({k: catalog[k] for k in ("goals", "products", "sections", "stop_codes", "alternatives")})
    pol["market"] = _read(root / "market.yaml")
    digest = hashlib.sha256(b"".join(f.read_bytes() for f in files)).hexdigest()[:8]
    pol["version"] = f"{pol['version']}+{digest}"
    return pol


@lru_cache
def sources(policy_dir: str | None = None) -> dict:
    return _read((Path(policy_dir) if policy_dir else POLICY_DIR) / "sources.yaml")
