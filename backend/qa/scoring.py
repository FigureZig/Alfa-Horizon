"""Проверка балльной карты на синтетике (docs/12 §7): различающая способность, точность, стабильность.

uv run python -m qa.scoring → docs/scoring_validation.md

Синтетический портфель — компании с правдоподобными распределениями факторов, прошедшие стоп-факторы политики.
«Истинный» риск — логистическая функция с другими весами, взаимодействием и шумом: иначе проверка была бы тавтологией,
карта угадывала бы сама себя. Дефолт за 12 месяцев разыгрывается по истинному PD; карта считает балл → PD → класс,
и мы сравниваем её с исходами. Детерминировано: фиксированные seed.
"""

import math
import random
from decimal import Decimal
from pathlib import Path

from app.domain.scoring import _points, score
from app.policy import load

OUT = Path(__file__).resolve().parents[2] / "docs" / "scoring_validation.md"
N, SEED = 10_000, 2026
# «истинная» модель: веса не совпадают с картой, есть взаимодействие «молодой бизнес × высокая нагрузка» и шум
TRUE = {"intercept": -5.0, "debt_load": 2.6, "inflow_cv": 1.3, "decline": 2.4, "overdue_1_5": 0.35, "overdue_6_30": 0.95,
        "overdue_31_plus": 1.9, "young": 0.8, "under_3y": 0.3, "requests": 0.17, "tax_debt": 0.55, "loss": 0.7,
        "bank_share": -0.5, "young_x_debt": 0.6, "noise": 0.35}


def _poisson(rng: random.Random, lam: float) -> int:
    k, p, limit = 0, 1.0, math.exp(-lam)
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def company(rng: random.Random, drift: float = 0.0) -> tuple[dict, str]:
    """drift > 0 — портфель в стрессе: выше нагрузка и разброс поступлений, чаще просрочка и запросы в БКИ."""
    segment = "IP" if rng.random() < 0.45 else "LLC"
    u = rng.random()
    overdue = 0 if u < 0.74 - 0.10 * drift else rng.randint(1, 5) if u < 0.88 else rng.randint(6, 30) if u < 0.96 \
        else rng.randint(31, 89)
    facts = {
        "age_months": int(min(300, max(6, rng.lognormvariate(math.log(40), 0.8)))),
        "inflow_cv": round(min(1.2, max(0.03, rng.betavariate(2.2, 5.5) * 1.1 + 0.15 * drift)), 4),
        "inflow_trend": round(max(-0.7, min(0.9, rng.gauss(0.03 - 0.15 * drift, 0.17))), 4),
        "debt_load": 0.0 if rng.random() < 0.38 - 0.10 * drift else round(min(0.9, rng.betavariate(2, 6) + 0.12 * drift), 4),
        "max_overdue_days": overdue,
        "bki_requests_30d": _poisson(rng, 1.1 + 1.5 * drift),
        "tax_debt": Decimal(0 if rng.random() < 0.86 - 0.08 * drift
                            else min(50_000, round(rng.lognormvariate(math.log(20_000), 0.8)))),
    }
    if segment == "LLC":
        facts["net_profit"] = Decimal(round(rng.gauss(0.05 - 0.03 * drift, 0.06) * 30_000_000))
        facts["bank_share"] = round(min(1.0, rng.betavariate(3, 2)), 4)
    return facts, segment


def true_pd(f: dict, segment: str, rng: random.Random) -> float:
    w, overdue, age = TRUE, f["max_overdue_days"], f["age_months"]
    z = (w["intercept"] + w["debt_load"] * f["debt_load"] + w["inflow_cv"] * f["inflow_cv"]
         + w["decline"] * max(0.0, -f["inflow_trend"]) + w["overdue_1_5"] * (1 <= overdue <= 5)
         + w["overdue_6_30"] * (6 <= overdue <= 30) + w["overdue_31_plus"] * (overdue > 30) + w["young"] * (age < 12)
         + w["under_3y"] * (age < 36) + w["requests"] * min(f["bki_requests_30d"], 10) + w["tax_debt"] * (f["tax_debt"] > 0)
         + w["young_x_debt"] * (age < 12 and f["debt_load"] > 0.3) + rng.gauss(0, w["noise"]))
    if segment == "LLC":
        z += w["loss"] * (f["net_profit"] <= 0) + w["bank_share"] * (f["bank_share"] - 0.6)
    return 1 / (1 + math.exp(-z))


def portfolio(n: int = N, seed: int = SEED, drift: float = 0.0) -> list[dict]:
    rng, card = random.Random(seed), load()["scorecard"]
    out = []
    for _ in range(n):
        facts, segment = company(rng, drift)
        pd = true_pd(facts, segment, rng)
        risk = score(facts, segment, card)
        out.append({"facts": facts, "segment": segment, "true_pd": pd, "default": rng.random() < pd,
                    "score": risk["score"], "pd": risk["pd"], "class": risk["class"]})
    return out


def auc(rows: list[dict]) -> float:
    """Площадь под ROC: вероятность, что у случайного «хорошего» балл выше, чем у случайного «плохого» (ничьи — пополам)."""
    ranked = sorted(rows, key=lambda r: r["score"])
    ranks, i = {}, 0
    while i < len(ranked):
        j = i
        while j < len(ranked) and ranked[j]["score"] == ranked[i]["score"]:
            j += 1
        for k in range(i, j):
            ranks[id(ranked[k])] = (i + j + 1) / 2
        i = j
    goods = [r for r in rows if not r["default"]]
    n_good, n_bad = len(goods), len(rows) - len(goods)
    return (sum(ranks[id(r)] for r in goods) - n_good * (n_good + 1) / 2) / (n_good * n_bad)


def ks(rows: list[dict]) -> float:
    bad_total = sum(r["default"] for r in rows)
    good_total = len(rows) - bad_total
    best = bad = good = 0
    for r in sorted(rows, key=lambda r: r["score"]):
        bad += r["default"]
        good += not r["default"]
        best = max(best, abs(bad / bad_total - good / good_total))
    return best


def wilson(defaults: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = defaults / n
    centre, spread = p + z * z / (2 * n), z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - spread) / (1 + z * z / n), (centre + spread) / (1 + z * z / n)


def calibration(rows: list[dict], classes: list[str]) -> list[dict]:
    out = []
    for cls in classes:
        group = [r for r in rows if r["class"] == cls]
        defaults = sum(r["default"] for r in group)
        low, high = wilson(defaults, len(group))
        predicted = sum(r["pd"] for r in group) / len(group) if group else 0
        out.append({"class": cls, "n": len(group), "share": len(group) / len(rows), "defaults": defaults,
                    "dr": defaults / len(group) if group else 0, "ci": (low, high), "pd": predicted,
                    "inside": low <= predicted <= high})
    return out


def psi(base: list[dict], other: list[dict], bins: int = 10) -> float:
    """Индекс стабильности распределения баллов: < 0,1 — стабильно, 0,1–0,25 — заметный сдвиг, > 0,25 — существенный."""
    scores = sorted(r["score"] for r in base)
    edges = sorted({scores[int(len(scores) * k / bins)] for k in range(1, bins)})

    def shares(rows):
        counts = [0] * (len(edges) + 1)
        for r in rows:
            counts[sum(r["score"] >= e for e in edges)] += 1
        return [max(c / len(rows), 1e-6) for c in counts]

    expected, actual = shares(base), shares(other)
    return sum((a - e) * math.log(a / e) for e, a in zip(expected, actual, strict=True))


def factors(rows: list[dict], card: dict) -> list[dict]:
    """По каждому фактору: доля дефолтов по интервалам карты, монотонность (больше баллов — меньше дефолтов) и IV."""
    out = []
    for name, f in card["factors"].items():
        groups: dict[int, list[bool]] = {}
        for r in rows:
            if r["segment"] not in f.get("segments", [r["segment"]]) or r["facts"].get(f["fact"]) is None:
                continue
            groups.setdefault(_points(r["facts"][f["fact"]], f["bins"]), []).append(r["default"])
        bads, goods = sum(sum(g) for g in groups.values()), sum(len(g) - sum(g) for g in groups.values())
        cells, iv = [], 0.0
        for points in sorted(groups):
            g = groups[points]
            b_share, g_share = max(sum(g) / bads, 1e-6), max((len(g) - sum(g)) / goods, 1e-6)
            iv += (g_share - b_share) * math.log(g_share / b_share)
            cells.append({"points": points, "n": len(g), "dr": sum(g) / len(g)})
        drs = [c["dr"] for c in cells if c["n"] >= 30]
        out.append({"factor": name, "reason": f["reason"], "cells": cells, "iv": iv,
                    "monotone": all(a >= b for a, b in zip(drs, drs[1:], strict=False))})
    return out


def fit_scale(rows: list[dict], base_score: int) -> dict:
    """Логистическая калибровка на балле: ln(odds «хорошего») = α + β·балл (Ньютон по двум параметрам).
    Отсюда шкала карты: PDO = ln 2 / β, odds при базовом балле = exp(α + β·база)."""
    alpha, beta = 0.0, 0.0
    xs = [(r["score"] - base_score) / 100 for r in rows]
    ys = [0.0 if r["default"] else 1.0 for r in rows]
    for _ in range(25):
        g0 = g1 = h00 = h01 = h11 = 0.0
        for x, y in zip(xs, ys, strict=True):
            p = 1 / (1 + math.exp(-(alpha + beta * x)))
            g0, g1 = g0 + (y - p), g1 + (y - p) * x
            w = p * (1 - p)
            h00, h01, h11 = h00 + w, h01 + w * x, h11 + w * x * x
        det = h00 * h11 - h01 * h01
        alpha, beta = alpha + (h11 * g0 - h01 * g1) / det, beta + (h00 * g1 - h01 * g0) / det
    beta_per_point = beta / 100
    return {"odds_at_base": math.exp(alpha), "pdo": math.log(2) / beta_per_point, "alpha": alpha, "beta": beta_per_point}


def recalibrated(rows: list[dict], scale: dict, base_score: int, classes: list[str]) -> list[dict]:
    out = []
    for c in calibration(rows, classes):
        group = [r for r in rows if r["class"] == c["class"]]
        pds = [1 / (1 + scale["odds_at_base"] * 2 ** ((r["score"] - base_score) / scale["pdo"])) for r in group]
        pd = sum(pds) / max(len(pds), 1)
        out.append({**c, "pd": pd, "inside": c["ci"][0] <= pd <= c["ci"][1]})
    return out


def pricing(cal: list[dict], pol: dict) -> list[dict]:
    """Покрывает ли цена риска наблюдаемые потери: спред за риск против ожидаемых потерь при наблюдаемой доле дефолтов."""
    rp, out = pol["risk_pricing"], []
    lgd = rp["lgd"]["none"]
    for c in cal:
        priced = rp["pd_for_price"][c["class"]]
        spread = priced * lgd * 100 + rp["opex_margin_pp"]
        out.append({"class": c["class"], "pd_for_price": priced, "dr": c["dr"], "el_observed_pp": c["dr"] * lgd * 100,
                    "spread_pp": spread, "covered": c["dr"] * lgd * 100 <= spread})
    return out


def validate(n: int = N) -> dict:
    pol = load()
    card, classes = pol["scorecard"], [c["class"] for c in pol["scorecard"]["classes"]]
    base = portfolio(n, SEED)
    fresh, stress = portfolio(n, SEED + 1), portfolio(n, SEED + 2, drift=0.6)
    a, cal = auc(base), calibration(base, classes)
    scale = fit_scale(base, card["base"])
    return {"n": n, "default_rate": sum(r["default"] for r in base) / n, "auc": a, "gini": 2 * a - 1, "ks": ks(base),
            "calibration": cal, "scale_now": card["pd_scale"], "scale_fit": scale,
            "recalibrated": recalibrated(base, scale, card["base"], classes), "pricing": pricing(cal, pol),
            "psi_fresh": psi(base, fresh), "psi_stress": psi(base, stress),
            "stress_default_rate": sum(r["default"] for r in stress) / n, "factors": factors(base, card)}


def _pct(x: float, digits: int = 1) -> str:
    return f"{100 * x:.{digits}f}%".replace(".", ",")


def _num(x: float, digits: int = 3) -> str:
    return f"{x:.{digits}f}".replace(".", ",")


def render(v: dict) -> str:
    cal, rec, scale, now = v["calibration"], v["recalibrated"], v["scale_fit"], v["scale_now"]
    order = [c["dr"] for c in cal if c["n"]]
    weak = [f["factor"] for f in v["factors"] if f["iv"] < 0.02]
    flat = [f["factor"] for f in v["factors"] if not f["monotone"]]
    lines = [
        "# Проверка скоринговой карты на синтетике",
        "",
        "Сгенерировано: `cd backend && uv run python -m qa.scoring` (фиксированные seed — те же цифры при каждом запуске). "
        "Карта — `backend/policy/policy-*.yaml` (`scorecard`), методика — `12_scoring.md` §7. Синтетика проверяет "
        "методику и код, а не реальный риск: на данных банка тот же отчёт строится той же программой.",
        "",
        "## Как устроена проверка",
        f"- **Портфель:** {v['n']} компаний, ИП и ООО (45 / 55%), прошедших стоп-факторы политики. Распределения факторов "
        "правдоподобные: возраст — логнормальный с медианой 40 мес., разброс поступлений — бета, тренд — нормальный, "
        "38% без кредитов, просрочка у 26%, запросы в БКИ — пуассоновские, недоимка у 14%.",
        "- **Истина отличается от карты:** дефолт разыгрывается по логистической функции с другими весами, "
        "взаимодействием «бизнес моложе года × нагрузка выше 30%» и шумом. Веса: "
        + ", ".join(f"`{k}` {str(w).replace('.', ',')}" for k, w in TRUE.items()) + ".",
        "- **Что меряем:** различающую способность (AUC, Gini, KS), точность (PD класса против наблюдаемой доли дефолтов "
        "с 95% интервалом Уилсона) и калибровку шкалы, достаточность цены риска, стабильность (PSI), монотонность и "
        "информационную ценность (IV) каждого фактора.",
        "",
        "## Различающая способность",
        "",
        "| Показатель | Значение | Ориентир |",
        "|---|---|---|",
        f"| Доля дефолтов в портфеле за 12 мес. | {_pct(v['default_rate'])} | МСП — единицы процентов |",
        f"| AUC | {_num(v['auc'])} | ≥ 0,70 — рабочая карта |",
        f"| Gini = 2·AUC − 1 | {_num(v['gini'])} | ≥ 0,40 |",
        f"| KS | {_num(v['ks'])} | ≥ 0,30 |",
        "",
        "## Точность и калибровка шкалы",
        "",
        f"Шкала карты: odds «хороший : плохой» = {now['odds_at_base']} при балле 600, удвоение каждые {now['pdo']} баллов. "
        f"Логистическая калибровка на синтетике даёт odds {_num(scale['odds_at_base'], 2)} и PDO {_num(scale['pdo'], 1)}: "
        "порядок классов карта держит, а уровень PD у текущей шкалы оптимистичный.",
        "",
        "| Класс | Компаний | Доля | Наблюдаемая доля дефолтов (95% интервал) | PD по текущей шкале | В интервале | "
        "PD после калибровки | В интервале |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for c, r in zip(cal, rec, strict=True):
        observed = f"{_pct(c['dr'], 2)} ({_pct(c['ci'][0], 2)} – {_pct(c['ci'][1], 2)})"
        lines.append(f"| {c['class']} | {c['n']} | {_pct(c['share'])} | {observed} | {_pct(c['pd'], 2)} | "
                     f"{'да' if c['inside'] else 'нет'} | {_pct(r['pd'], 2)} | {'да' if r['inside'] else 'нет'} |")
    lines += [
        "",
        f"Доля дефолтов растёт от A к D: {'да' if all(a <= b for a, b in zip(order, order[1:], strict=False)) else 'нет'}.",
        "",
        "## Покрывает ли цена риска потери",
        "",
        "Спред за риск в ставке = PD класса для цены × LGD + 1,5 п.п. (`risk_pricing`). Сравниваем его с ожидаемыми потерями "
        "при наблюдаемой доле дефолтов и тех же LGD 50% (без залога).",
        "",
        "| Класс | PD для цены | Наблюдаемая доля дефолтов | Ожидаемые потери, п.п. | Спред за риск, п.п. | Покрывает |",
        "|---|---|---|---|---|---|",
    ]
    lines += [f"| {p['class']} | {_pct(p['pd_for_price'])} | {_pct(p['dr'], 2)} | {_num(p['el_observed_pp'], 2)} | "
              f"{_num(p['spread_pp'], 2)} | {'да' if p['covered'] else 'нет'} |" for p in v["pricing"]]
    lines += [
        "",
        "## Стабильность",
        "",
        "| Сравнение | PSI | Вывод |",
        "|---|---|---|",
        f"| Новая выборка из того же портфеля | {_num(v['psi_fresh'])} | {_psi_text(v['psi_fresh'])} |",
        f"| Портфель в стрессе: нагрузка, просрочка и запросы выше | {_num(v['psi_stress'])} | {_psi_text(v['psi_stress'])}; "
        f"доля дефолтов {_pct(v['stress_default_rate'])} |",
        "",
        "PSI — сигнал мониторинга: распределение баллов сдвинулось → пересмотреть пороги классов, лимиты и цену риска.",
        "",
        "## Факторы: монотонность и информационная ценность",
        "",
        "| Фактор | Причина | Доля дефолтов по интервалам (баллы → доля, компаний) | Монотонно | IV |",
        "|---|---|---|---|---|",
    ]
    for f in v["factors"]:
        cells = " · ".join(f"{c['points']:+d} → {_pct(c['dr'])} ({c['n']})" for c in f["cells"])
        lines.append(f"| {f['factor']} | {f['reason']} | {cells} | {'да' if f['monotone'] else 'нет'} | {_num(f['iv'])} |")
    lines += [
        "",
        "IV: < 0,02 — почти ничего не добавляет, 0,02–0,1 — слабый, 0,1–0,3 — средний, > 0,3 — сильный.",
        "",
        "## Выводы для политики",
        "",
        f"1. Ранжирование рабочее (Gini {_num(v['gini'], 2)}), но уровень PD текущей шкалы ниже наблюдаемого: при переходе "
        f"на реальные данные — перекалибровать `pd_scale` (по синтетике odds ≈ {_num(scale['odds_at_base'], 1)}, "
        f"PDO ≈ {_num(scale['pdo'], 0)}), классы и пороги при этом не меняются.",
        "2. Цена риска классов, где ожидаемые потери выше спреда, — кандидат на пересмотр `pd_for_price`: ставка должна "
        "покрывать потери, иначе рост портфеля в этих классах убыточен.",
        f"3. Немонотонные факторы ({', '.join(flat) or 'нет'}): интервалы, где больше баллов не значит меньше дефолтов, — "
        "кандидаты на объединение.",
        f"4. Слабые факторы по IV ({', '.join(weak) or 'нет'}) оставлены ради объяснимости и политики, но различающей "
        "способности почти не добавляют.",
        "",
    ]
    return "\n".join(lines)


def _psi_text(value: float) -> str:
    return "стабильно" if value < 0.1 else "заметный сдвиг" if value < 0.25 else "существенный сдвиг"


def main() -> None:
    OUT.write_text(render(validate()), "utf-8")
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
