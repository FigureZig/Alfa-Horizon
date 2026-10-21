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
```

## Моки WireMock: как устроены
- **Демо-мир** — `seed/personas.yaml`: люди, компании, отрасли, обороты по месяцам, кредиты в БКИ, недоимки, контракты и ожидаемые исходы.
- **Генератор** — `uv run python seed/gen_mocks.py` пересобирает `wiremock/`: тела в форматах из `docs/09` (ЕГРЮЛ 4.06, XSD ФНС, ГИР БО, ЦБ v3.4)
  и по одному файлу стабов на ручку. Тело выбирается по ИНН шаблоном (`{{request.pathSegments.[3]}}`, `{{jsonPath request.body '$.subject.inn'}}`),
  незнакомый ИНН получает 404. Руками JSON не правим; CI сверяет, что моки совпадают с `personas.yaml`.
- **Приоритеты стабов:** 1 — отказы песочницы, 3 — персоны, собранные на лету (дальше), 5 — штатный мир, 9 — «не найдено».
- **Отказы на лету** — `POST /api/v1/sandbox/faults` ставит стаб с приоритетом 1, `DELETE …/faults/{id}` снимает, `POST /sandbox/reset` возвращает штатный мир. Без перезапусков.

## Как добавить
| Что | Где |
|---|---|
| компанию или сценарий | `seed/personas.yaml` (+ `scenario.expect`) → `gen_mocks.py` → тест подхватит сам |
| продукт, отрасль, цель | `policy/products.yaml`; ставки ЦБ — `policy/market.yaml` |
| порог, скоринг, текст причины | новый `policy/policy-<версия>.yaml` |
| внешний источник | `policy/sources.yaml` + разбор в `app/features.py` + тело в генераторе |
| ручку API | `app/api/client.py`, `bank.py` или `sandbox.py`; потом перевыгрузить `docs/openapi.json` (`uv run python -m app.openapi > ../docs/openapi.json`) |

## Что дальше
SSE для таймлайна · права «человек × компания» (`rights.py`) · K1 радар разрыва (`forecast.py`) · оферта: принять, подписать, выдать в АБС с ключом идемпотентности ·
решение специалиста и второй ключ · дедлайны ожидания источника (`RETRY_WAIT` → специалисту) · типизированные ответы API.
