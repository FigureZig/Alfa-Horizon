"""Проверки ядра, которые не зависят от деталей спеки: граф статусов, pairwise-набор персон, инварианты чисел.

Используются тестами (tests/test_state_graph.py, tests/test_mechanics.py) и генератором отчёта
(uv run python -m qa.report → docs/test-scenarios.md). Зависимости — только dev (networkx, allpairspy).
"""
