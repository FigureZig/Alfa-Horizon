"""Отчёт о тестовых сценариях ядра: uv run python -m qa.report → docs/test-scenarios.md

Всё в отчёте вычисляется из кода (state.py, policy/, seed/world.py, qa/), руками его не правят.
Детерминирован: те же исходники — тот же файл (CI сверяет git diff).
"""

from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.domain import state
from app.policy import load
from seed import world

from . import graph, invariants, pairwise

OUT = Path(__file__).resolve().parents[2] / "docs" / "test-scenarios.md"
KIND = {"client": "клиент", "system": "конвейер", "timer": "таймер", "bank": "специалист"}


def _money(x) -> str:
    return f"{int(Decimal(x)):,}".replace(",", " ")


def _rate(x) -> str:
    return f"{Decimal(x):.1f}".replace(".", ",")


def _offer(d: dict) -> str:
    o = d["offer"]
    if not o:
        return "—"
    return f"{o['product']} {_money(o['amount'])} ₽ · {o['termMonths']} мес. · {_rate(o['rate']['total'])}%"


def _codes(d: dict) -> str:
    return ", ".join(dict.fromkeys(r["code"] for r in d["reasons"])) or "—"


def _section_graph(g) -> list[str]:
    kinds = Counter(k for ks in state.EDGES.values() for k in ks)
    checks = {
        "недостижимые из DRAFT статусы": graph.unreachable(g),
        "тупики: нетерминальный статус без пути к терминалу (deadlock)": graph.dead_ends(g),
        "замкнутые круги без выхода (livelock, сильно связные компоненты)": graph.closed_cycles(g),
        "терминалы с исходящими переходами": graph.terminal_exits(g),
    }
    return [
        "## 1. Жизненный цикл заявки как граф",
        "",
        f"Статусов {g.number_of_nodes()}, переходов {g.number_of_edges()}; инициаторы переходов: "
        + ", ".join(f"{KIND[k]} — {n}" for k, n in sorted(kinds.items())) + ". Таблица — `app/domain/state.py`.",
        "",
        "| Проверка | Результат |",
        "|---|---|",
        *[f"| {label} | {', '.join(sorted(map(str, found))) or 'нет'} |" for label, found in checks.items()],
        f"| статусы без выхода по таймеру или конвейеру | {', '.join(sorted(graph.can_hang(g)))} — ждёт специалиста, "
        "срок держит SLA |",
        "",
        "```mermaid",
        state.mermaid(),
        "```",
        "",
    ]


def _section_routes(g) -> list[str]:
    routes = graph.covering_routes(g)
    into_terminal = sum(1 for _, dst in state.EDGES if dst in state.TERMINAL)
    lines = [
        "## 2. Минимальный набор сквозных прогонов",
        "",
        f"{len(routes)} прогонов проходят все {g.number_of_edges()} переходов, всего {sum(len(r) - 1 for r in routes)} шагов. "
        f"Меньше нельзя: каждый прогон кончается одним из {into_terminal} переходов в терминал. Поиск — задача китайского "
        "почтальона: циркуляция минимальной стоимости с нижней границей 1 на переходе, затем разложение на кратчайшие пути "
        "и циклы, каждый цикл встроен в самый короткий подходящий прогон (`qa/graph.py`).",
        "",
        "| # | Итог | Маршрут (кто запускает шаг) | Шагов |",
        "|---|---|---|---|",
    ]
    for i, route in enumerate(routes, 1):
        steps = " ".join(f"→ _{'/'.join(KIND[k] for k in sorted(kinds))}_ → {b}" for _, b, kinds in graph.route_steps(g, route))
        lines.append(f"| {i} | {route[-1]} | DRAFT {steps} | {len(route) - 1} |")
    lines += ["", "Как вызвать каждый переход в демо:", "", "| Переход | Кто | Как |", "|---|---|---|"]
    lines += [f"| {a} → {b} | {', '.join(KIND[k] for k in sorted(state.EDGES[a, b]))} | {how} |"
              for (a, b), how in graph.HOW.items()]
    return lines + [""]


def _cases(pol: dict, today: date) -> dict[str, list[dict]]:
    out, number = {}, 0
    for name, vectors in (("healthy", pairwise.vectors(pairwise.HEALTHY)), ("faulty", pairwise.vectors(pairwise.FAULTY)),
                          ("stops", pairwise.stop_vectors())):
        out[name] = [pairwise.build(v, number + i + 1, pol, today) for i, v in enumerate(vectors)]
        number += len(vectors)
    return out


def _axes(axes: dict) -> str:
    return "; ".join(f"{name} ({len(values)}): {', '.join(values)}" for name, values in axes.items())


def _section_pairwise(cases: dict, pol: dict) -> list[str]:
    lines = [
        "## 3. Свои персоны: pairwise",
        "",
        "Персона строится из осей тем же `seed/world.py`, что демо-мир: ИНН и ОГРН с контрольными цифрами, выписка, "
        "кредиты в БКИ, отчётность — согласованы между собой. Ответы источников проходят через JSON, как из WireMock. "
        "Набор векторов — IPOG (allpairspy): каждая пара значений любых двух осей встречается хотя бы раз.",
        "",
        f"Профили: strong — класс A, average — B, weak — C, risky — D (`qa/pairwise.py`). Суммы: below_min — половина "
        f"минимума продукта, at_min — минимум, fits — посильная, large — около трети активов (крупная сделка), "
        f"above_authority — {_money(pol['params']['auto_authority_max'] + 2_000_000)} ₽.",
        "",
    ]
    for name, axes, extra in (("healthy", pairwise.HEALTHY, "term"), ("faulty", pairwise.FAULTY, "fault")):
        rows = cases[name]
        outcomes = Counter(c["decision"]["outcome"] for c in rows)
        title = "все источники отвечают — проверяются числа оферт" if name == "healthy" else \
            "упал источник или режим предодобрения — неизвестное не становится ни «да», ни «нет»"
        lines += [
            f"### 3.{1 if name == 'healthy' else 2}. {name}: {title}",
            "",
            f"Оси — {_axes(axes)}. Векторов: {len(rows)}; исходы: "
            + ", ".join(f"{k} {v}" for k, v in sorted(outcomes.items())) + ".",
            "",
            f"| # | Форма | Раздел | Продукт | Сумма | Профиль | {'Срок' if extra == 'term' else 'Сбой · режим'} "
            "| Исход | Класс | Оферта | Причины |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for i, c in enumerate(rows, 1):
            v, d = c["vector"], c["decision"]
            third = v["term"] if extra == "term" else f"{v['fault']} · {v['mode']}"
            lines.append(f"| {i} | {v['form']} | {v['section']} | {v['product']} | {v['amount']} | {v['profile']} | {third} | "
                         f"{d['outcome']} | {(d['risk'] or {}).get('class', '—')} | {_offer(d)} | {_codes(d)} |")
        lines.append("")
    return lines


def _section_stops(cases: dict) -> list[str]:
    table: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for c in cases["stops"]:
        d = c["decision"]
        table[c["vector"]["stop"], c["vector"]["fault"]][d["outcome"] + (f" {d['kind']}" if d["kind"] else "")] += 1
    lines = [
        "## 4. Стоп-факторы: полный перебор",
        "",
        "Стоп × форма бизнеса × сбой; остальное — средняя компания с посильным экспресс-кредитом. Правило: стоп виден "
        "в ответившем источнике → отказ нужного вида; источник молчит → не отказ (неизвестно ≠ плохо), а ручная "
        "проверка или предварительная оферта с подписью только после проверки.",
        "",
        "| Стоп-фактор | Источник | " + " | ".join(pairwise.STOP_FAULTS) + " |",
        "|---|---|" + "---|" * len(pairwise.STOP_FAULTS),
    ]
    for stop, (_, code, _kind, sources) in pairwise.STOPS.items():
        cells = [", ".join(f"{k} ×{n}" for k, n in sorted(table[stop, f].items())) for f in pairwise.STOP_FAULTS]
        lines.append(f"| {stop} ({code}) | {', '.join(sources)} | " + " | ".join(cells) + " |")
    return lines + [""]


def _section_invariants(cases: dict, pol: dict) -> list[str]:
    total = sum(len(v) for v in cases.values())
    broken = sum(1 for rows in cases.values() for c in rows
                 if invariants.check(c["decision"], c["facts"], c["request"], pol))
    offers = sum(1 for rows in cases.values() for c in rows if c["decision"]["offer"])
    lines = [
        "## 5. Инварианты",
        "",
        f"Проверяются на каждом из {total} векторов ({offers} с офертой); нарушений: {broken}. Код — `qa/invariants.py`, "
        "тест — `tests/test_mechanics.py`; что инварианты не пустые, проверяет тест на испорченном решении.",
        "",
    ]
    lines += [f"- {text}" for text in invariants.INVARIANTS]
    lines += [
        "",
        "Свойства на парах решений (метаморфные проверки):",
        "",
        "- больше поступлений → лимит не меньше; больше платежей по кредитам → лимит не больше;",
        "- при полных данных предодобрение (simulate) = решение по заявке (commit);",
        "- хуже класс → ставка не ниже и множитель лимита не выше; лучше обеспечение → ставка не выше (все разделы ОКВЭД);",
        "- стоп виден в источнике → отказ нужного вида; источник молчит → не отказ.",
        "",
    ]
    return lines


def render(today: date | None = None) -> str:
    pol = load()
    today = today or date.fromisoformat(world.load()["today"])
    g = graph.status_graph()
    cases = _cases(pol, today)
    lines = [
        "# Тестовые сценарии ядра",
        "",
        "Сгенерировано из кода: `cd backend && uv run python -m qa.report`. Руками не править — источник правды: "
        "`app/domain/state.py`, `policy/`, `seed/world.py`, `qa/`. Конкретные числа демо-мира держат golden-сценарии "
        f"(`tests/test_scenarios.py`, `seed/personas.yaml`). Политика {pol['version']}, дата мира {today.isoformat()}.",
        "",
        *_section_graph(g),
        *_section_routes(g),
        *_section_pairwise(cases, pol),
        *_section_stops(cases),
        *_section_invariants(cases, pol),
        "## 6. Как запустить",
        "",
        "```bash",
        "cd backend",
        "uv run pytest                      # всё: golden, граф, pairwise, инварианты, мир и моки",
        "uv run python -m qa.report         # пересобрать этот файл",
        "uv run python -m seed.gen_mocks    # пересобрать моки WireMock из seed/personas.yaml",
        "```",
        "",
        "Своя персона в живом стенде: `POST /api/v1/sandbox/personas` (параметры — как у осей выше), ответ — ИНН; "
        "worker сразу подтягивает её данные из WireMock.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    OUT.write_text(render(), "utf-8")
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
