# 06. Архитектура

Ground truth по устройству системы. Архитектура как код — `diagrams/architecture.c4` (LikeC4, проверка `npx likec4 validate diagrams`).
C4 с потоками данных — `diagrams/c4-data-flows.drawio`: L2 (контейнеры и ручки), L3 (модули API и слой K), L3-W (Worker: интеграции и устойчивость).
Ручки и поля внешних систем — `09_data_contracts.md`. Устойчивость — `07_resilience.md`.

**Принцип: минимум кода.** 5 таблиц, один http-клиент на все источники, правила и продукты в YAML, всё остальное вычисляется. Сценарии от этого не меняются.

Исходные ограничения: неделя, 1–2 бэкендера, офисный ПК 8–16 ГБ без GPU, запуск одной командой (в том числе на Windows), жюри оценивает обоснованность и enterprise-мышление,
впереди финал — архитектура должна расти без переписывания.

## 1. Решение одной схемой
```
Браузер ─HTTP:8080─▶ web (nginx): статика Vue SPA + reverse proxy /api  ── один origin, без CORS
                        │
                        ▼
                     api (FastAPI, модульный монолит) ──SSE──▶ браузер
                        │  REST /api/v1, OpenAPI 3.1; наружу НЕ ходит, читает снапшоты
                        ▼
                     postgres 17 (5 таблиц) ◀── jobs: SKIP LOCKED · events: NOTIFY ──▶ worker (тот же пакет, другой entrypoint)
                                                                         │ единственный, кто вызывает внешние ручки
                                                                         ▼
                                              wiremock: ЕГРЮЛ, ЕГРИП, ФНС, ГИР БО, БКИ, МЧД, юр. проверки, банк, АБС, ЕИС
                                              (штатные стабы по реальным форматам + стабы отказов из песочницы)
   migrate (one-shot: alembic upgrade + seed) · (опционально, вне Docker) Ollama — OpenAI-compatible, не в пути решения
```
| Компонент | Решение | Почему |
|---|---|---|
| api | модульный монолит FastAPI | одна транзакционная сущность (заявка) → без распределённых транзакций; модули выносятся в сервисы позже |
| worker | тот же пакет, отдельный процесс | конвейер, ретраи, таймеры не блокируют API и не падают вместе с ним |
| postgres | единственное хранилище: заявки, события, очередь задач, снапшоты | ноль доп. инфраструктуры, нет dual-write |
| wiremock | внешний мир по HTTP, реальные форматы, отказы на лету через admin API | настоящая граница интеграции; мок заменяется реальным API сменой адаптера |
| web | nginx | один порт и origin для проверяющего, prod-подобно |

Брокер не нужен: transactional outbox + `SELECT … FOR UPDATE SKIP LOCKED` [P1]. Путь в прод — outbox-relay в Kafka без изменения домена.

## 2. Код: минимум слоёв
```
backend/
  app/
    domain/          чистая логика без IO, тестируется таблицами
      calc.py        калькуляторы: аннуитет, обратная задача, график, проценты, K4 (13 §7)
      catalog.py     продукты × отрасли, ставка из частей, ограничения суммы и лимит (13 §2–6)
      scoring.py     балльная карта (12)
      engine.py      решение: стоп-факторы → продукт → требования → скоринг → ставка и лимит → контрпредложение → исход + трасса
      state.py       таблица переходов, флаги, исход → статус; диаграмма генерируется из неё
      okved.py       раздел ОКВЭД 2 по коду
      (дальше: rights.py — права «человек × компания», forecast.py — K1)
    features.py      анти-коррупционный слой: ответы реестров (форматы 09) → факты движка
    sources.py       один http-клиент на все источники: таймаут, ретраи с jitter, breaker в kv, снапшоты
    store.py         5 таблиц (asyncpg + SQL, JSONB); переход статуса + событие + задача в одной транзакции
    company.py       факты о компании из снапшотов с происхождением (STALE_OK, БКИ — только свежий)
    api/             FastAPI: client.py, bank.py, sandbox.py (только DEMO_MODE); sse.py — дальше
    worker.py        цикл задач: обновление снапшотов, конвейер заявки, ретраи
  policy/            policy-2026.10-1.yaml (пороги, скоринг, цена риска, тексты причин) · products.yaml (продукты, отрасли, цели) ·
                     market.yaml (КС и ставки ЦБ с источником) · sources.yaml (ручки, TTL, таймауты, отказы песочницы)
  migrations/        SQL-миграции (001_init.sql — 5 таблиц)
  seed/              personas.yaml — демо-мир; gen_mocks.py — генератор моков
  wiremock/          mappings + __files — генерируются из seed, руками не правим
  tests/             табличные, golden по демо-миру; дальше — отказы N1–N17
```
Правила: `domain/` не импортирует IO — единственный контракт import-linter; всё про K лежит в `domain/` отдельными функциями и вызывается только при включённом флаге;
песочница регистрируется только при `DEMO_MODE`. Логические модули с C4 (parties, applications, decisioning, insights, tasks, signing, loans, audit) — это функции этих файлов,
а не отдельные пакеты и таблицы.

## 3. Паттерны и где они
| Паттерн | Где | Зачем | Ссылка |
|---|---|---|---|
| Явный state machine (таблица переходов + guards) | applications | из таблицы генерируем диаграмму и тесты всех переходов; недопустимый переход невозможен | — |
| Порты и адаптеры + анти-коррупционный слой | integrations, `RiskModel`, `LlmPort` | мок ↔ реальный API, правила ↔ ML без изменения ядра; форматы реестров не протекают в домен | [P9] |
| Правила как данные, таблицы решений DMN | decisioning, catalog | политика меняется без релиза, версия в каждом решении, табличные тесты | [P10] |
| Transactional outbox: таблицы `events` и `jobs` пишутся в одной транзакции с заявкой; потребители идемпотентны | api → worker | статус и задача атомарны, события не теряются | [P1] |
| Оркестрируемый конвейер с чекпоинтами (сага без компенсаций до выдачи) | worker | шаг можно перезапустить с чекпоинта; видно, где застряли | [P2] |
| Idempotency-Key на командах | подать, принять, подписать, выдать | двойной клик и ретраи не создают дублей; деньги ровно один раз | [P3] |
| Таймауты, ретраи с backoff и jitter (в одном слое) | integrations | не добивать упавший источник, не умножать ретраи | [P4] |
| Circuit breaker, bulkhead | integrations | быстрый отказ при аварии источника; медленный БКИ не блокирует ЕГРЮЛ | [P5], [P6] |
| Снапшоты с TTL, stale-while-revalidate | integrations → API | кабинет работает, когда реестры лежат | [P7] |
| Фича-флаги | `FEATURE_K1…K5`, `DEMO_MODE`, `LLM_ENABLED` | доп. слой включается без риска для основы | [P8] |
| Оптимистическая блокировка (`version`) | заявка | гонки бухгалтер ↔ директор, аналитик ↔ таймер | — |
| Неизменяемая запись решения | decisioning | снимок входа, версия политики, причины → аудит и воспроизводимость | — |
| Maker-checker | ручные исключения аналитика | четыре глаза | [P14] |
| Хэш-цепочка аудита | audit | подмену записи видно | [P19] |
| Tenant scoping | весь API | IDOR: чужую заявку по id не открыть | — |
| Problem Details | ошибки API | машинный `code` + человеческий текст | [P20] |
| Trace context | api → jobs → worker → wiremock | одна заявка = один след в логах | [P21] |

Осознанно не берём: микросервисы, event sourcing, CQRS, service mesh, GraphQL — на отборе это сложность без выигрыша.

## 4. Модель данных: 5 таблиц
| Таблица | Что хранит | Ключевые поля |
|---|---|---|
| `applications` | заявка целиком: запрос, текущая оферта и варианты, открытые дозапросы, подписи, решения органов, выдача и график после ISSUED | id, company_inn, status, flags[], data jsonb, version, updated_at |
| `events` | история и аудит: переходы, решения с трассой, подписи, согласия, действия песочницы; только добавление; после вставки NOTIFY → SSE | id, at, application_id, type, actor, payload jsonb, idempotency_key (unique), prev_hash, hash |
| `jobs` | очередь и таймеры: шаги конвейера, ретраи, сроки, дедлайны, выдача | id, kind, application_id, payload jsonb, status, attempts, run_at, lease_until, last_error |
| `snapshots` | ответы реестров и банка с происхождением; при сбое источника последний удачный ответ сохраняется | source, key, payload jsonb, fetched_at, status, error, hash |
| `kv` | операционные мелочи: breaker по источникам, персона демо, часы песочницы, пауза воркера | key, value jsonb, updated_at |

Отдельных таблиц нет, потому что это вычисляется или лежит в YAML:
- права — из снапшотов на лету; inbox задач — запрос по заявкам в статусах ожидания + права;
- сигналы и офферы K1/K2 — из транзакций на лету; принятый оффер — обычная заявка;
- продукты, правила, скоринг, параметры — `policy/*.yaml` в git; версия политики = имя файла + hash, пишется в каждое решение;
- согласия, подписи, решения движка — события; последнее решение и оферта дублируются в `applications.data` для быстрого чтения;
- кредит после выдачи — `applications.data.loan`; ключ идемпотентности выдачи = id заявки;
- отказы песочницы — метаданные стабов в самом WireMock.

Миграции — SQL-файлы в `backend/migrations/`, применяются по порядку (`python -m app.migrate`); ORM нет: asyncpg + SQL, Pydantic — только для входа API.
Деньги — `Decimal`, в JSON — строка; даты — ISO 8601 с часовым поясом.

## 5. API (контракт для фронта; OpenAPI 3.1 генерирует FastAPI)
REST `/api/v1`, действия — подресурсами, ошибки RFC 9457, заголовки `Idempotency-Key`, `X-Request-Id`, cursor-пагинация.
| Группа | Ручки |
|---|---|
| Персона и компании | `GET /me` · `GET /me/companies` (с правами) · `GET /companies/{inn}/capabilities` (с «почему» и нормой) · `GET /companies/{inn}/profile` (что банк знает: факты, источники, даты) |
| Подбор и офферы | `GET /companies/{inn}/products?goal=&amount=&term=` · `GET /companies/{inn}/insights` (K1, K2, K5 по флагам) · `POST /insights/offers/{id}/accept` |
| Заявка | `POST /applications` · `PATCH /applications/{id}` · `POST …/{id}/submit` · `POST …/{id}/withdraw` · `GET …/{id}` · `GET …/{id}/timeline` (шаги и флаги) · `GET …/{id}/events` (SSE) · `GET …/{id}/explain` |
| Согласия и дозапросы | `POST …/{id}/consents` · `GET …/{id}/info-requests` · `POST …/info-requests/{rid}/answer` |
| Корпоративные решения | `GET …/{id}/approvals` · `POST /approvals/{aid}/vote` (если устав допускает технические средства) |
| Оферта и подпись | `GET …/{id}/offer` (варианты, K4-симуляция, K3) · `POST …/{id}/offer/accept` · `POST …/{id}/offer/decline` · `POST …/{id}/signatures` |
| Задачи | `GET /tasks` · `POST /tasks/{tid}/complete` |
| Кредит | `GET /loans/{id}` |
| Система | `GET /system/integrations` (здоровье источников для баннеров) · `/health/live` · `/health/ready` |
| Банк (кредитный специалист, Must) | `GET /bank/queue` · `GET /bank/applications/{id}/dossier` · `POST /bank/applications/{id}/decision` · `POST /bank/decisions/{did}/confirm` (второй ключ) |
| Песочница (`DEMO_MODE`) | `GET /sandbox/presets` · `POST /sandbox/personas` · `POST /sandbox/events` · `POST /sandbox/faults` · `DELETE /sandbox/faults/{id}` · `POST /sandbox/worker/pause` · `POST /sandbox/worker/resume` · `POST /sandbox/clock` · `POST /sandbox/reset` |

## 6. События и задачи
- **Типы событий** (`events.type`): `application.status_changed` · `decision.made` (исход, вид оферты, причины, трасса, версия политики) · `step.changed` · `consent.given` ·
  `signature.added` · `registry.changed` · `source.health_changed` · `insight.signal` · `sandbox.*`. После вставки — NOTIFY → SSE в открытые вкладки.
- **Виды задач** (`jobs.kind`): `pipeline_step` · `timer` (оферта, дозапрос, подпись, черновик) · `deadline` (ожидание источника) · `disburse` · `recheck`.
  Воркер берёт задачи `FOR UPDATE SKIP LOCKED`, обработчики идемпотентны; статусы задачи — машина шага конвейера (`diagrams/application_state.md` §2).
- Outbox — это и есть `events` + `jobs`: пишутся в одной транзакции с изменением заявки [P1].

## 7. Запуск и деплой
- `docker compose up --build` — одна команда, работает без правки `.env`. Сервисы: `postgres`, `migrate`, `api`, `worker`, `wiremock`, `web`; healthchecks и `depends_on: service_healthy`.
- Профили: по умолчанию prod-подобный; `dev` (hot-reload); `test` (прогон автотестов, включая тесты отказов).
- Env: `DEMO_MODE`, `FEATURE_K1…K5`, `LLM_ENABLED`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, таймауты и SLO-дедлайны интеграций.
- WireMock: `--global-response-templating`; `mappings/` — по одному стабу на ручку, `__files/<источник>/<ИНН>.json` — тела (§12).
- Бюджет RAM ≈ 0,8–1 ГБ (postgres 200, api 150, worker 150, wiremock 256 с `-Xmx256m`, nginx 10) при лимите 8–16 ГБ.
- Windows: `.gitattributes` `* text=auto eol=lf`, без Makefile как единственного способа, порты 8080 и 55432.
- Страховка: VM + тот же compose + Caddy (HTTPS); CI собирает образы в GHCR.

## 8. Репозиторий и процесс
Монорепо без сабмодулей: `backend/` — всё бэковое (api + worker, `policy/`, `migrations/`, `seed/`, `wiremock/` — моки генерируются из `seed/`), `frontend/`, `deploy/`, `docs/` (`openapi.json`), ``.
Trunk-based, короткие ветки, PR + ревью + зелёный CI, merge без squash (история коммитов видна жюри), Conventional Commits, CODEOWNERS, тег версии на дедлайн.
CI: ruff, mypy (по возможности), pytest (движок, state machine, сценарии, отказы, идемпотентность), import-linter, OpenAPI drift check, `likec4 validate`.

## 9. Стек
Python 3.13 · FastAPI · Pydantic v2 · asyncpg + SQL-миграции · uv + `uv.lock` · httpx · PyYAML · pytest · ruff · PostgreSQL 17 · WireMock 3.9 (Apache-2.0) · nginx.
Фронт — Vue 3 + PrimeVue + Tailwind (команда фронта). Всё перечисляем в `THIRD_PARTY_NOTICES` вместе со списком смоделированных интеграций.

## 10. Безопасность и сопровождение (минимум для enterprise)
Демо-JWT от мок-SSO; права вычисляются из снапшотов (`rights`) в каждой команде; tenant scoping; аудит всех решений и переходов; ПДн только синтетические; секретов в репо нет;
`DEMO_MODE` выключает песочницу целиком (эндпоинты не регистрируются). Логи JSON с `X-Request-Id`; здоровье интеграций — в API и песочнице; метрики (доля STP,
время решения, срабатывания политик фактов, состояние breaker) — Should.

## 11. Путь роста (потенциал развития)
Адаптеры к реальным реестрам и БКИ вместо моков · `RiskModel` на ML с объяснением вкладов · Kafka через outbox-relay · вынос `decisioning` и `integrations` в сервисы ·
OpenTelemetry · HA PostgreSQL · КЭП и криптопроверка МЧД · комитет и полномочия по суммам · OCR документов дозапроса.

## 12. Как не плодить бойлерплейт
- **WireMock:** по одному файлу стабов на ручку. Шаблон выбирает тело по ИНН — `"bodyFileName": "egrul/{{request.pathSegments.[3]}}.json"`, для POST —
  `{{jsonPath request.body '$.subject.inn'}}` [P18]; известные ИНН перечислены в шаблоне пути, незнакомый ИНН получает 404, как в настоящем реестре.
  Тела `__files/<источник>/<ИНН>.json`, включая операции по счёту за 12 месяцев, генерирует `backend/seed/gen_mocks.py` из `seed/personas.yaml`; руками JSON не пишем.
  Персона из «Кто я» — тот же генератор, тело уходит через admin API (приоритет 3); отказы — admin API (приоритет 1); штатный мир — приоритет 5.
- **Источники:** один http-клиент + `sources.yaml` вместо класса на источник; Pydantic-модель ответа — только на поля, которые используем.
- **Хранилище:** 5 таблиц, SQLAlchemy Core, одна миграция.
- **Логика:** правила, таблицы, скоринг, продукты — YAML; движок их читает, отдельного кода под каждое правило нет.
- **Тесты:** один раннер прогоняет все сценарии из пресетов (S, R, N) и сверяет с golden-файлами.

