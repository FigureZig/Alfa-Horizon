# Бэкенд

FastAPI (API) + worker в одном пакете, PostgreSQL (5 таблиц), WireMock вместо реестров. Логика — `docs/04`, `docs/12`, `docs/13`; устройство — `docs/06`.

## Как это работает
```
браузер → api ──читает──▶ snapshots ◀──пишет── worker ──HTTP──▶ wiremock (ЕГРЮЛ, ЕГРИП, ФНС, ГИР БО, БКИ, банк, ЕИС…)
           └─ ставит задачи в jobs ─────────────▶ worker: факты → движок → статус заявки + события
```
1. Worker обновляет **снапшоты** компании: по ручке на источник из `policy/sources.yaml`, с таймаутом, ретраями и breaker.
2. `app/features.py` превращает ответы реестров в **факты**: отрасль, возраст бизнеса, обороты, недоимка, нагрузка из БКИ…
3. `app/domain/engine.py` по фактам и политике решает: стоп-факторы → продукт для отрасли → скоринг → ставка и лимит → исход.
4. Решение, причины и трасса пишутся в заявку и в `events`; статус меняется только по таблице `app/domain/state.py`.

## Запуск
Всё одной командой из этой папки:
```bash
cp .env.example .env          # необязательно: без .env подставятся те же значения
docker compose up --build     # postgres, migrate, api, worker, wiremock
```
Для разработки без пересборки образа — база и моки в Docker, код локально:
```bash
docker compose up -d postgres wiremock
uv sync
uv run --env-file .env python -m app.migrate
uv run --env-file .env uvicorn app.main:app --reload --port 8000   # http://localhost:8000/api/docs
uv run --env-file .env python -m app.worker
uv run pytest
```
`.env` в git не попадает; шаблон — `.env.example`.

## Проверить руками
```bash
A=localhost:8000/api/v1
curl -X POST $A/companies/770100000079/refresh                                   # worker сходит в реестры
curl "$A/companies/770100000079/products?goal=cash_gap&amount=400000"            # подбор: предодобрено / условно / недоступно
curl -X POST $A/applications -H 'content-type: application/json' \
     -d '{"inn":"770100000079","product":"OVERDRAFT","amount":400000,"goal":"cash_gap","consent_bki":true}'
curl -X POST $A/applications/<id>/submit -H 'Idempotency-Key: 1'                 # → решение через пару секунд
curl $A/applications/<id>
curl -X POST $A/sandbox/faults -H 'content-type: application/json' \
     -d '{"source":"bki","mode":"timeout","inn":"770100000142"}'                 # сломать БКИ на лету; режимы: timeout, error503, reset, garbage, empty
curl $A/bank/queue                                                               # исключения у специалиста
curl -X POST $A/sandbox/personas -H 'content-type: application/json' \
     -d '{"kind":"LLC","okved":"46.90","inflow_avg":4000000,"participants":2}'    # своя персона → ИНН, worker сразу тянет данные
```

## Моки WireMock: как устроены
- **Демо-мир** — `seed/personas.yaml`: люди, компании, отрасли, обороты по месяцам, кредиты в БКИ, недоимки, контракты и ожидаемые исходы.
- **Генератор** — `uv run python -m seed.gen_mocks` пересобирает `wiremock/`: тела в форматах из `docs/09` (ЕГРЮЛ 4.06, XSD ФНС, ГИР БО, ЦБ v3.4)
  и по одному файлу стабов на ручку. Тело выбирается по ИНН шаблоном (`{{request.pathSegments.[3]}}`, `{{jsonPath request.body '$.subject.inn'}}`),
  незнакомый ИНН получает 404. Руками JSON не правим; тест и CI сверяют, что моки совпадают с `personas.yaml`.
- **Правила мира** — `seed/world.py`: контрольные цифры ИНН/ОГРН/СНИЛС, согласованность источников (категория МСП из численности
  и дохода, платёж по кредиту в выписке = платёж в БКИ, отметки ЕГРЮЛ только у юрлиц). Платежи и остатки кредитов выводятся
  из суммы, ставки и срока, а не пишутся руками.
- **Своя персона** — `POST /api/v1/sandbox/personas`: компания из параметров профиля → те же `world.py` и проверка → стабы
  с приоритетом 3 через admin API WireMock → worker обновляет снапшоты. `GET …/personas` — список, `POST …/reset` — убрать.
- **Приоритеты стабов:** 1 — отказы песочницы, 3 — свои персоны, 5 — штатный мир, 9 — «не найдено».
- **Отказы на лету** — `POST /api/v1/sandbox/faults` ставит стаб с приоритетом 1, `DELETE …/faults/{id}` снимает, `POST /sandbox/reset` возвращает штатный мир. Без перезапусков.

## Как добавить
| Что | Где |
|---|---|
| компанию или сценарий | `seed/personas.yaml` (+ `scenario.expect`) → `uv run python -m seed.gen_mocks` → тест подхватит сам |
| продукт, отрасль, цель | `policy/products.yaml`; ставки ЦБ — `policy/market.yaml` |
| порог, скоринг, текст причины | новый `policy/policy-<версия>.yaml` |
| внешний источник | `policy/sources.yaml` + разбор в `app/features.py` + тело в генераторе |
| статус или переход | `app/domain/state.py` (+ кто запускает) и способ вызвать в демо — `qa/graph.py` `HOW`; тесты графа подхватят сами |
| ручку API | `app/api/client.py`, `bank.py` или `sandbox.py`; потом перевыгрузить контракт (`uv run python -m app.openapi > ../docs/api/openapi.json`) |

## Тесты
`uv run pytest` — за полсекунды, без БД и сети: ответы источников строятся в памяти тем же `seed/world.py` и проходят через JSON.
| Что | Где | Как |
|---|---|---|
| golden-сценарии демо-мира | `tests/test_scenarios.py` | точные числа и исходы из `scenario.expect` |
| граф статусов | `tests/test_state.py`, `qa/graph.py` | достижимость, тупики, круги без выхода, «не зависает», 16 прогонов покрывают все 31 переход |
| механика на своих персонах | `tests/test_mechanics.py`, `qa/pairwise.py`, `qa/invariants.py` | pairwise (IPOG) по форме, отрасли, продукту, сумме, профилю, сроку, сбою; инварианты чисел; монотонность |
| сущности и моки | `tests/test_world.py` | контрольные цифры, согласованность источников, моки = мир, стабы своей персоны = запросы worker |
Сводка сценариев для людей — `docs/test-scenarios.md`, пересобирается `uv run python -m qa.report`.

## Что дальше
SSE для таймлайна · права «человек × компания» (`rights.py`) · K1 радар разрыва (`forecast.py`) · оферта: принять, подписать, выдать в АБС с ключом идемпотентности ·
решение специалиста и второй ключ · дедлайны ожидания источника (`RETRY_WAIT` → специалисту) · типизированные ответы API.
