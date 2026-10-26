# Как работать с репозиторием

Правила для всех, кто меняет код. Цель простая: после любого PR стенд поднимается одной командой, а код, документация и контракт API говорят одно и то же.

## Зоны и ветки

| Зона | Папка | Владелец |
|---|---|---|
| Бэкенд, база данных, моки внешних систем | `backend/` | @FigureZig |
| Фронтенд | `frontend/` | @lyublyukotikov |
| Стенд целиком | `infra/` | @FigureZig |
| Документация | `docs/` | @FigureZig |

- Одна задача — одна ветка и один PR. Ветки называем по смыслу: `feat/…`, `fix/…`, `docs/…`.
- Работаем в своей зоне. Чужую папку, lock-файлы другой зоны, CI и общие файлы (`README.md`, `docs/api/openapi.json`, `infra/docker-compose.yml`, `.env.example`) меняем отдельным PR под задачу.
- Логика описана в `docs/`, контракт API лежит в `docs/api/openapi.json`. Если код с ними расходится, сначала заводим issue, потом меняем код.
- Без массового реформата, без `.env` и секретов в коммитах, без force-push в общие ветки.

## Перед PR

Бэкенд:

```bash
cd backend
uv run ruff check . && uv run pytest    # линтер и юнит-тесты
uv run pytest -m e2e                    # если трогали API, заявку или worker; нужны Postgres и WireMock стенда
```

Если поменяли логику, кредитную политику или мир симулятора, пересоберите документы, которые генерируются из кода. CI сверяет их с кодом и падает, если они устарели:

```bash
uv run python -m qa.report                                # docs/test-scenarios.md
uv run python -m qa.roles                                 # docs/15_roles.md
uv run python -m qa.scoring                               # docs/scoring_validation.md
uv run python -m qa.postman                               # docs/api/postman_collection.json
uv run python -m qa.er                                    # docs/diagrams/data_model.md
uv run python -m app.openapi > ../docs/api/openapi.json   # контракт API
```

Фронтенд: `cd frontend && pnpm lint && pnpm build`.

Стенд: `cd infra && docker compose up --build` поднимается без ошибок.

## Бэкенд: договорённости

- **Логика отдельно от ввода-вывода.** Правила и расчёты живут в `app/domain/` и не импортируют `store`, `sources`, `httpx`. Ответы внешних систем разбирает только `app/features.py`.
- **Во внешние системы ходит только worker** через `app/sources.py`. API читает сохранённые снимки данных и ставит задачи в очередь.
- **Деньги — `Decimal`**, `float` в расчётах не используем. В JSON заявки сумма уходит строкой: `"400000.00"` (`app/jsonutil.py`).
- **Числа кредитной политики — в YAML.** Пороги, продукты, отрасли и тексты причин лежат в `policy/*.yaml`, а не в коде. Новая политика — новый файл `policy-<версия>.yaml`.
- **Моки руками не правим.** Меняем мир в `seed/personas.yaml` и пересобираем моки: `uv run python -m seed.gen_mocks`.
- **Ответы и ошибки единообразны.** Ответ отдаём через `ok()` (`{"data": …}`), ошибку — через `Problem(status, code, detail)` в формате RFC 9457. Поля называем в snake_case. Права проверяет `deps.require` до выполнения команды.
- **Новый переход или действие с заявкой** требует трёх правок: команда в `app/lifecycle.py`, способ вызвать переход в симуляторе в `qa/graph.py` (`HOW`) и действие в `tests/e2e/test_routes.py` (`ACTIONS`). Без них тесты упадут.
- **Новый сценарий** — компания в `seed/personas.yaml` с `scenario.expect`. Её проверит `tests/test_scenarios.py`.
- **Тесты держат инварианты.** Правило проверяют инварианты `qa/invariants.py` на pairwise-наборах тестовых компаний, а не отдельный юнит-тест на каждый случай. Нашли новый класс ошибки — добавьте инвариант.

## Фронтенд: договорённости

Стиль, структура, компоненты, типы и сервисы описаны в [`frontend/CONTRIBUTING.md`](frontend/CONTRIBUTING.md).
