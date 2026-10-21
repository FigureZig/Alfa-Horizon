# Бэкенд: правила для агентов

- Чистая логика — `app/domain/`: без IO, без импорта `store`, `sources`, `httpx`. Форматы внешних систем разбирает только `app/features.py`.
- Деньги — `Decimal`, в JSON — строкой (`app/jsonutil.py`). Никогда `float`.
- Цифры, пороги, продукты, отрасли, тексты причин — в `policy/*.yaml`, не в коде. Поменял кредитную политику — новый файл `policy-<версия>.yaml`.
- Во внешние системы ходит только worker через `app/sources.py`; API читает снапшоты и ставит задачи.
- Моки руками не правим: меняем `seed/personas.yaml` → `uv run python -m seed.gen_mocks`.
- Новый сценарий = компания в `seed/personas.yaml` со `scenario.expect` — её проверит `tests/test_scenarios.py`.
- Новый переход в `app/domain/state.py` — сразу способ вызвать его в демо в `qa/graph.py` (`HOW`), иначе тест упадёт.
- Юнит-тесты на каждое правило не пишем: правило должно держаться инвариантами `qa/invariants.py` на pairwise-персонах.
  Нашёл класс ошибки — добавь инвариант, а не отдельный тест на случай.
- Поменял логику, политику или мир — пересобери `docs/test-scenarios.md`: `uv run python -m qa.report`.
- Перед PR: `uv run ruff check . && uv run pytest`.
