"""Граф статусов заявки (app/domain/state.py) как данные: достижимость, тупики, замкнутые циклы, зависания
и минимальный набор сквозных прогонов, который проходит каждый переход хотя бы раз.

Минимальный набор — задача китайского почтальона для маршрутов DRAFT → терминал: циркуляция минимальной
стоимости с нижней границей 1 на каждом переходе (network simplex). Поток раскладываем на кратчайшие пути
DRAFT → терминал и циклы; каждый цикл встраиваем в самый короткий прогон, который через него проходит, —
так прогон остаётся читаемой историей, а не одним длинным обходом.
"""

from collections import Counter, deque

import networkx as nx

from app.domain.state import EDGES, STATUSES, TERMINAL

START = "DRAFT"
SINK = "__end__"
WAITS_FOR_BANK = frozenset({"UNDER_REVIEW"})   # выход только по решению специалиста; срок держит SLA (флаг SLA_BREACH)
_ROUTE_COST = 10_000                          # прогон дороже любого числа шагов: сначала меньше прогонов, потом короче
_ORDER = list(EDGES)                          # порядок обхода — как в state.py, результат детерминирован

# Как вызвать переход в демо (docs/02, docs/07 §5, docs/08). Новый переход без способа вызвать его — тест упадёт.
HOW = {
    ("DRAFT", "SUBMITTED"): "клиент подаёт заявку",
    ("DRAFT", "WITHDRAWN"): "клиент удаляет черновик или 30 дней без подачи",
    ("SUBMITTED", "CHECKING"): "worker берёт задачу конвейера",
    ("SUBMITTED", "WITHDRAWN"): "клиент отзывает до старта конвейера (воркер на паузе)",
    ("CHECKING", "OFFERED"): "решение APPROVE / COUNTER_OFFER / APPROVE_WITH_CONDITIONS (пресеты S7, S3, S8)",
    ("CHECKING", "INFO_REQUESTED"): "решение REQUEST_INFO (пресет S2: крупная сделка без согласия участников)",
    ("CHECKING", "UNDER_REVIEW"): "решение MANUAL_REVIEW (S5: выше полномочий) или источник не ответил до дедлайна (N2)",
    ("CHECKING", "REJECTED"): "решение REJECT (S4: недоимка)",
    ("CHECKING", "WITHDRAWN"): "клиент отзывает во время проверки (воркер на паузе)",
    ("INFO_REQUESTED", "CHECKING"): "клиент отвечает на системный дозапрос — конвейер заново",
    ("INFO_REQUESTED", "UNDER_REVIEW"): "клиент отвечает на дозапрос специалиста",
    ("INFO_REQUESTED", "EXPIRED"): "срок ответа истёк (сдвиг часов песочницы)",
    ("INFO_REQUESTED", "WITHDRAWN"): "клиент отзывает",
    ("UNDER_REVIEW", "OFFERED"): "специалист одобряет на экране банка",
    ("UNDER_REVIEW", "INFO_REQUESTED"): "специалист запрашивает документ",
    ("UNDER_REVIEW", "REJECTED"): "специалист отказывает",
    ("UNDER_REVIEW", "WITHDRAWN"): "клиент отзывает",
    ("OFFERED", "SIGNING"): "клиент принимает оферту",
    ("OFFERED", "DECLINED"): "клиент отказывается от оферты",
    ("OFFERED", "EXPIRED"): "срок оферты истёк (сдвиг часов)",
    ("OFFERED", "CHECKING"): "событие мира: изменились данные реестра — пересмотр (RECHECK, N17)",
    ("OFFERED", "WITHDRAWN"): "клиент отзывает",
    ("SIGNING", "SIGNED"): "подписали все, кто должен (ЕИО или представитель по МЧД)",
    ("SIGNING", "EXPIRED"): "срок подписи истёк (сдвиг часов)",
    ("SIGNING", "CHECKING"): "событие мира до подписи — пересмотр (RECHECK)",
    ("SIGNING", "WITHDRAWN"): "клиент отзывает",
    ("SIGNED", "DISBURSING"): "перепроверка по свежим данным пройдена",
    ("SIGNED", "REJECTED"): "при перепроверке всплыл стоп-фактор (ГК ст. 821 п. 1)",
    ("SIGNED", "WITHDRAWN"): "клиент отказывается от получения (ГК ст. 821 п. 2)",
    ("DISBURSING", "ISSUED"): "АБС подтвердила зачисление",
    ("DISBURSING", "UNDER_REVIEW"): "сбой АБС до дедлайна (отказ abs в песочнице, N7)",
}


def status_graph() -> nx.DiGraph:
    g = nx.DiGraph()
    g.add_nodes_from(STATUSES)
    for (src, dst), kinds in EDGES.items():
        g.add_edge(src, dst, kinds=kinds)
    return g


def unreachable(g: nx.DiGraph) -> set[str]:
    """Статусы, в которые не попасть из DRAFT."""
    return set(g) - nx.descendants(g, START) - {START}


def dead_ends(g: nx.DiGraph) -> set[str]:
    """Нетерминальные статусы, из которых не дойти ни до одного терминала (deadlock)."""
    return {s for s in g if s not in TERMINAL and not nx.descendants(g, s) & TERMINAL}


def terminal_exits(g: nx.DiGraph) -> set[str]:
    """Терминалы, из которых есть переходы, — терминал перестал быть концом."""
    return {s for s in TERMINAL if g.out_degree(s)}


def closed_cycles(g: nx.DiGraph) -> list[set[str]]:
    """Компоненты сильной связности без выхода наружу (livelock): заявка ходит по кругу и не завершается."""
    out = []
    for scc in nx.strongly_connected_components(g):
        cyclic = len(scc) > 1 or any(g.has_edge(s, s) for s in scc)
        if cyclic and all(dst in scc for s in scc for dst in g.successors(s)):
            out.append(scc)
    return out


def can_hang(g: nx.DiGraph) -> set[str]:
    """Статусы без перехода по таймеру или конвейеру: если клиент ушёл, заявка ждёт вечно."""
    return {s for s in g if s not in TERMINAL and not any(g.edges[s, d]["kinds"] & {"system", "timer"} for d in g.successors(s))}


def _cover_counts(g: nx.DiGraph) -> tuple[Counter, int]:
    """Сколько раз каждый переход входит в оптимальный набор и сколько в нём прогонов.

    Нижняя граница 1 снимается заменой f = f' + 1: спрос вершины = исходящие − входящие переходы.
    """
    h = nx.DiGraph()
    for s in g:
        h.add_node(s, demand=g.out_degree(s) - g.in_degree(s))
    h.add_node(SINK, demand=0)
    h.add_edges_from(g.edges, weight=1)
    h.add_edges_from(((t, SINK) for t in TERMINAL), weight=0)
    h.add_edge(SINK, START, weight=_ROUTE_COST)
    _, flow = nx.network_simplex(h)
    return Counter({(s, d): flow[s][d] + 1 for s, d in g.edges}), flow[SINK][START]


def _shortest(left: Counter) -> list[str]:
    prev, queue = {START: None}, deque([START])
    while queue:
        node = queue.popleft()
        if node in TERMINAL:
            path = [node]
            while prev[path[-1]] is not None:
                path.append(prev[path[-1]])
            return path[::-1]
        for s, d in _ORDER:
            if s == node and left[s, d] > 0 and d not in prev:
                prev[d] = node
                queue.append(d)
    raise ValueError("в остатке потока нет пути DRAFT → терминал")


def _closed_walk(left: Counter) -> list[str]:
    """В циркуляции обход из вершины может застрять только в ней самой — получаем замкнутый маршрут."""
    start = next(s for s, d in _ORDER if left[s, d] > 0)
    walk = [start]
    while True:
        edge = next(e for e in _ORDER if e[0] == walk[-1] and left[e] > 0)
        left[edge] -= 1
        walk.append(edge[1])
        if edge[1] == start:
            return walk


def covering_routes(g: nx.DiGraph) -> list[list[str]]:
    """Наименьшее число прогонов DRAFT → терминал, вместе проходящих все переходы; при равном числе — короче в сумме.

    Прогонов не меньше, чем переходов в терминалы: каждый прогон кончается ровно одним таким переходом.
    """
    left, n_routes = _cover_counts(g)
    routes = []
    for _ in range(n_routes):
        path = _shortest(left)
        left.subtract(zip(path, path[1:], strict=False))
        routes.append(path)
    cycles = []
    while +left:
        cycles.append(_closed_walk(left))
    for cyc in sorted(cycles, key=len, reverse=True):
        _, i, j = min((len(r), i, j) for i, r in enumerate(routes) for j, node in enumerate(r[:-1]) if node in cyc)
        node, ring = routes[i][j], cyc[:-1]
        k = ring.index(node)
        routes[i] = routes[i][:j] + ring[k:] + ring[:k] + routes[i][j:]
    return sorted(routes, key=lambda r: (STATUSES.index(r[-1]), len(r)))


def route_steps(g: nx.DiGraph, route: list[str]) -> list[tuple[str, str, frozenset[str]]]:
    return [(a, b, g.edges[a, b]["kinds"]) for a, b in zip(route, route[1:], strict=False)]


def uncovered(g: nx.DiGraph, routes: list[list[str]]) -> set[tuple[str, str]]:
    seen = {(a, b) for r in routes for a, b in zip(r, r[1:], strict=False)}
    return set(g.edges) - seen
