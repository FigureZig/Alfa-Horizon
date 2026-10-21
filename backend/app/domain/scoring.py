"""Балльная карта (docs/12): балл, PD, класс риска и вклад каждого фактора. Карта — в политике, расчёт — здесь."""


def _points(value, bins: list[dict]) -> int:
    for b in bins:
        if "lt" in b and not value < b["lt"]:
            continue
        if "le" in b and not value <= b["le"]:
            continue
        return b["points"]
    raise ValueError("последний бин должен быть без условия")


def score(facts: dict, segment: str, card: dict, *, skip_sources: tuple[str, ...] = ()) -> dict:
    """skip_sources: источники, чьи факты неизвестны (например, БКИ без согласия) — их факторы дают 0 баллов."""
    total, contributions, missing = card["base"], [], []
    for factor, f in card["factors"].items():
        if segment not in f.get("segments", [segment]):
            continue
        value = None if f.get("source") in skip_sources else facts.get(f["fact"])
        if value is None:
            missing.append(factor)
            contributions.append({"factor": factor, "value": None, "points": 0, "reason": f["reason"]})
            continue
        points = _points(value, f["bins"])
        if "two_payments_skipped" in f and facts.get("two_payments_skipped"):
            points = min(points, f["two_payments_skipped"])
        total += points
        contributions.append({"factor": factor, "value": value, "points": points, "reason": f["reason"]})

    total = max(card["min"], min(card["max"], total))
    scale = card["pd_scale"]
    odds = scale["odds_at_base"] * 2 ** ((total - card["base"]) / scale["pdo"])
    risk_class = next(c["class"] for c in card["classes"] if total >= c["min"])
    weakest = sorted((c for c in contributions if c["points"] < 0), key=lambda c: c["points"])[:3]
    return {
        "score": total,
        "pd": round(1 / (1 + odds), 4),
        "class": risk_class,
        "contributions": contributions,
        "missing": missing,
        "weak": [c["reason"] for c in weakest],   # три самых отрицательных вклада → «почему так» и рычаги K3
    }
