# Бэкенд

FastAPI (API) + worker в одном пакете, PostgreSQL (5 таблиц), WireMock вместо реестров. Логика — `docs/04`, `docs/12`, `docs/13`; устройство — `docs/06`.
Документация API — Swagger http://localhost:8000/api/docs и ReDoc http://localhost:8000/api/redoc; схемы ответов — `app/api/schemas.py`.

## Как это работает
```
браузер → api ──читает──▶ snapshots ◀──пишет── worker ──HTTP──▶ wiremock (ЕГРЮЛ, ЕГРИП, ФНС, ГИР БО, БКИ, банк, ЕИС…)
           └─ ставит задачи в jobs ─────────────▶ worker: факты → движок → статус заявки + события
```
1. Вход пользователем (`/sandbox/personas/{id}/login`) → JWT; worker берёт карточку клиента в банке и собирает его компании.
2. Worker обновляет **снапшоты** компании: по ручке на источник из `policy/sources.yaml`, с таймаутом, ретраями и breaker.
3. `app/features.py` превращает ответы реестров в **факты**, `app/domain/rights.py` — в **права** человека в компании (ЕГРЮЛ, ЕГРИП, ДБО).
4. `app/domain/engine.py` по фактам и политике решает: стоп-факторы → продукт для отрасли → скоринг → ставка и лимит → исход.
5. `app/lifecycle.py` ведёт заявку дальше: оферта, подпись, голосование участников, финальная проверка и выдача в АБС, дозапрос,
   решение специалиста и второй ключ риск-менеджера, сроки. Кнопки каждой роли — `lifecycle.actions` → `available_actions`.
   Статус меняется только по таблице `app/domain/state.py`, каждое изменение — событие в `events` в той же транзакции.

## Запуск
Весь стенд с фронтом — `cd ../infra && docker compose up --build`. Только бэкенд — из этой папки:
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
uv run pytest                 # юнит: без базы и сети
uv run pytest -m e2e          # сквозные: нужны postgres и wiremock из compose, база credit_e2e создаётся сама
```
`.env` в git не попадает; шаблон — `.env.example`.

## Проверить руками
Ответ — `{"data": …}`, ошибка — RFC 9457 с `code` (соглашения — `docs/api/README.md`). Без токена запрос идёт от последнего вошедшего пользователя.
```bash
A=localhost:8000/api/v1
curl "$A/sandbox/personas?lang=ru"                                               # кто есть на экране входа
curl -X POST $A/auth/login -H 'content-type: application/json' -d '{"login":"s7"}'   # войти по ID → data.token
curl $A/me                                                                       # компании и права с нормами
curl $A/dashboard                                                                # остаток, обороты, предложение в 1 клик
curl $A/companies/770100000079/insights                                          # K1: прогноз остатка, разрыв 28.10; K2: предложение
curl $A/companies/770100000079/score                                             # балл, PD, класс, вклады факторов и рычаги
curl -X POST $A/applications -H 'content-type: application/json' \
     -d '{"inn":"770100000079","product":"OVERDRAFT","amount":400000,"goal":"cash_gap","consent_bki":true}'
curl -X POST $A/applications/<id>/submit -H 'Idempotency-Key: 1'                 # → решение через пару секунд
curl -X POST $A/applications/<id>/offer/accept                                   # → SIGNING
curl -X POST $A/applications/<id>/signatures                                     # → SIGNED → финальная проверка → АБС → ISSUED
curl $A/applications/<id>                                                        # статус, оферта, available_actions, loan
curl $A/applications/<id>/explain                                                # почему так: скоринг, ставка из частей, путь к одобрению
curl -X POST $A/sandbox/faults -H 'content-type: application/json' \
     -d '{"source":"bki","mode":"timeout","inn":"770100000142"}'                 # сломать БКИ на лету; режимы: timeout, error503, reset, garbage, empty
curl -X POST $A/sandbox/events -H 'content-type: application/json' \
     -d '{"type":"legal.bankruptcy_started","inn":"770100000079"}'               # событие мира → пересмотр оферт компании
curl -X POST $A/sandbox/clock -H 'content-type: application/json' -d '{"advance_s":3600}'   # истекают оферты и подписи
curl -X POST "$A/sandbox/personas/bank/login" && curl $A/bank/queue              # кредитный специалист: очередь исключений
curl -X POST "$A/sandbox/personas/risk/login"                                    # риск-менеджер: второй ключ выше 15 млн ₽
curl -X POST $A/bank/applications/<id>/decision/confirm -H 'content-type: application/json' -d '{"approve":true}'
curl -X POST $A/sandbox/personas -H 'content-type: application/json' \
     -d '{"full_name":"Анна Петрова","organization":"ООО «Ромашка»","form":"LLC","okved":"46.90","inflow_avg":4000000}'
```

## Моки WireMock: как устроены
- **Мир симулятора** — `seed/personas.yaml`: люди, компании, отрасли, обороты по месяцам, кредиты в БКИ, недоимки, контракты и ожидаемые исходы.
- **Генератор** — `uv run python -m seed.gen_mocks` пересобирает `wiremock/`: тела в форматах из `docs/09` (ЕГРЮЛ 4.06, XSD ФНС, ГИР БО, ЦБ v3.4)
  и по одному файлу стабов на ручку. Тело выбирается по ИНН шаблоном (`{{request.pathSegments.[3]}}`, `{{jsonPath request.body '$.subject.inn'}}`),
  незнакомый ИНН получает 404. Руками JSON не правим; тест и CI сверяют, что моки совпадают с `personas.yaml`.
- **Правила мира** — `seed/world.py`: контрольные цифры ИНН/ОГРН/СНИЛС, согласованность источников (категория МСП из численности
  и дохода, платёж по кредиту в выписке = платёж в БКИ, отметки ЕГРЮЛ только у юрлиц). Платежи и остатки кредитов выводятся
  из суммы, ставки и срока, а не пишутся руками.
- **Своя компания** — `POST /api/v1/sandbox/personas`: компания из параметров профиля → те же `world.py` и проверка → стабы
  с приоритетом 3 через admin API WireMock → worker обновляет снапшоты. `GET …/personas` — список, `POST …/reset` — убрать.
- **Приоритеты стабов:** 1 — отказы симулятора, 2 — события мира, 3 — свои компании, 5 — штатный мир, 9 — «не найдено».
- **Отказы на лету** — `POST /api/v1/sandbox/faults` ставит стаб с приоритетом 1, `DELETE …/faults/{id}` снимает, `POST /sandbox/reset` возвращает штатный мир. Без перезапусков.

## Как добавить
| Что | Где |
|---|---|
| компанию или сценарий | `seed/personas.yaml` (+ `scenario.expect`) → `uv run python -m seed.gen_mocks` → тест подхватит сам |
| продукт, отрасль, цель | `policy/products.yaml`; ставки ЦБ — `policy/market.yaml` |
| порог, скоринг, текст причины | новый `policy/policy-<версия>.yaml` |
| внешний источник | `policy/sources.yaml` + разбор в `app/features.py` + тело в генераторе |
| статус или переход | `app/domain/state.py` (+ кто запускает) и способ вызвать в симуляторе — `qa/graph.py` `HOW`; тесты графа подхватят сами |
| ручку API | `app/api/client.py`, `cabinet.py`, `bank.py` или `sandbox.py`; потом перевыгрузить контракт (`uv run python -m app.openapi > ../docs/api/openapi.json`) |
| роль или сценарий со сменой ролей | права — `app/domain/rights.py`, кнопки — `lifecycle.actions`, сценарий — `seed/flows.py` → `uv run python -m qa.roles` |

## Тесты
`uv run pytest` — за полсекунды, без БД и сети: ответы источников строятся в памяти тем же `seed/world.py` и проходят через JSON.
| Что | Где | Как |
|---|---|---|
| golden-сценарии мира симулятора | `tests/test_scenarios.py` | точные числа и исходы из `scenario.expect` |
| граф статусов | `tests/test_state.py`, `qa/graph.py` | достижимость, тупики, круги без выхода, «не зависает», 16 прогонов покрывают все переходы; диаграмма в docs = таблица в коде |
| механика на своих персонах | `tests/test_mechanics.py`, `qa/pairwise.py`, `qa/invariants.py` | pairwise (IPOG) по форме, отрасли, продукту, сумме, профилю, сроку, сбою; инварианты чисел; монотонность |
| сущности и моки | `tests/test_world.py` | контрольные цифры, согласованность источников, моки = мир, стабы своей персоны = запросы worker |
| права | `tests/test_rights.py` | ИП, директор, дисквалификация, недостоверность, участник ООО и АО, ДБО, совместные директора |
| K1 и K3 | `tests/test_forecast.py`, `tests/test_levers.py` | регулярные платежи и разрыв S7; каждый рычаг улучшает решение, у неустранимого рычагов нет |
| скоринг на синтетике | `tests/test_scoring_validation.py`, `qa/scoring.py` | AUC и KS, порядок классов, калибровка, PSI, монотонность сильных факторов |
| контракт API | `tests/test_api_contract.py` | конверт `{data}`, ошибки RFC 9457, CORS, `X-Request-Id`, DTO кабинета |
| **сквозные** (`-m e2e`) | `tests/e2e/test_routes.py`, `test_session.py`, `test_flows.py`, `test_cabinet.py`, `test_mocks.py`, `test_simulator.py` | 16 прогонов графа через HTTP API: каждый переход вызывает тот, кто его делает (клиент, конвейер, таймер, специалист, событие мира); вход по ID и карточкой, права R8, главная, своя компания с флагами, N1; 9 сценариев со сменой ролей и токенов, гид по сценариям, живой таймлайн (SSE); кабинет в контракте фронта и рабочее место банка; WireMock отвечает как мир. Каждый успешный ответ сверяется со схемой OpenAPI своей ручки |
| флаги своей компании | `tests/test_persona_flags.py` | каждый флаг на эталонной заявке даёт обещанную причину, продукт или отказ источника — без флага этого нет |
| документация API | `tests/test_api_contract.py` | у каждой ручки русское название, схема ответа, ошибки RFC 9457, вход Bearer |
Документы из кода (CI сверяет, что они актуальны): `docs/test-scenarios.md` — `uv run python -m qa.report`, `docs/15_roles.md` —
`uv run python -m qa.roles`, `docs/scoring_validation.md` — `uv run python -m qa.scoring`, коллекция запросов
`docs/api/postman_collection.json` — `uv run python -m qa.postman` (CI прогоняет её `newman` по стенду в Docker).

## Что дальше
КЭП и криптопроверка МЧД ·
смена директора на лету (R12) · несколько компаний у своего пользователя · типизированные ответы API (pydantic-модели в OpenAPI).
