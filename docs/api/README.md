# API: как с ним работать фронту

Контракт — [`openapi.json`](openapi.json). Живая документация: Swagger — http://localhost:8000/api/docs (кнопка **Authorize**
для токена, примеры тел запросов), ReDoc — http://localhost:8000/api/redoc (то же самое для чтения, с группами «Клиент», «Банк»,
«Симулятор»); короткие адреса `/docs` и `/redoc` ведут туда же, через стенд — http://localhost:8080/api/docs. У каждой ручки —
русское название, схема успешного ответа и возможные ошибки; что ответы совпадают со схемами, проверяют сквозные тесты.
Здесь — соглашения и какие ручки за какими экранами.
Коллекция запросов — [`postman_collection.json`](postman_collection.json): импорт в Postman, запуск папок по порядку в Collection Runner
или `docker run --rm --network host -v "$PWD:/etc/newman" postman/newman:6-alpine run postman_collection.json` из этой папки при поднятом стенде.

## Соглашения
- **Адрес.** `VITE_API_BASE_URL=http://localhost:8000/api` при `pnpm dev` (CORS для 5173 и 4173 открыт) или `/api` за nginx стенда `infra/`
  (тот же origin). Пути — `v1/…`.
- **Успех** — `{"data": …}`; у списков `data` — массив. Иногда рядом `meta`.
- **Ошибка** — RFC 9457, `Content-Type: application/problem+json`: `{"type", "title", "status", "detail", "code", …}`. Текст `detail` — для людей,
  ветвиться — по `code`. У 422 — `errors: [{loc, msg, type}]`, у 403 — `right`, `roles`, `why` (почему нельзя, с нормой закона).
- **Поля** — snake_case (в DTO — как есть, в сущности — camelCase через маппер).
- **Деньги** — строкой с копейками: `"400000.00"`. Это намеренно — Decimal без потерь; для отображения `Number(...)` в маппере, считать на фронте не нужно.
  Исключение — витрина кабинета (`companies/{inn}/insights`, `…/products`, `…/applications/summary`, `demo-personas/*`): там числа, как в DTO фронта.
- **Даты** — ISO 8601. **Статусы, коды причин, продукты** — строковые enum, значения как в контракте.
- **Вход** — по ID: `POST v1/auth/login {"login": "s7"}` (ID или код пользователя, ИНН человека, ИНН компании; незнакомый — 404
  `USER_NOT_FOUND`) или карточкой: `POST v1/sandbox/personas/{id}/login` → `data.token` → заголовок `Authorization: Bearer <token>`.
  Выход — `POST v1/auth/logout`. Без токена в симуляторе запрос идёт
  от последнего вошедшего пользователя (по умолчанию S7), а ручки компании по ИНН — от пользователя этой компании; поэтому страницы работают
  и до подключения входа. **Перелогин** — тот же вход другим пользователем: права и кнопки пересчитываются, заявки остаются.
- У каждого ответа — `X-Request-Id` (можно прислать свой); подача заявки принимает `Idempotency-Key`.

| code | когда |
|---|---|
| `VALIDATION_ERROR` | поля запроса не прошли проверку (`errors[]`) |
| `TOKEN_INVALID`, `LOGIN_REQUIRED`, `USER_UNKNOWN` | токен битый или истёк, нужен вход, пользователя больше нет |
| `FORBIDDEN`, `BANK_ONLY`, `ROLE_REQUIRED` | нет права в этой компании (`why`) · действие только для банка · только для риск-менеджера |
| `NOT_A_PARTICIPANT`, `NO_OPEN_APPROVAL`, `NOTARY_REQUIRED`, `SHAREHOLDERS_DECISION_REQUIRED` | голосуют только участники · голосование не открыто · устав требует нотариуса или решения акционеров — ответ через дозапрос |
| `AWAITING_SECOND_KEY`, `NOTHING_TO_CONFIRM`, `SAME_PERSON` | решение ждёт риск-менеджера · подтверждать нечего · второй ключ ставит другой сотрудник |
| `NOT_DECIDED`, `OFFER_VARIANT_UNKNOWN`, `AMOUNT_REQUIRED` | у заявки ещё нет решения · такого варианта оферты нет · специалисту — укажите сумму и срок |
| `COMPANY_REQUIRED`, `COMPANY_NOT_FOUND`, `NOT_A_CLIENT` | укажите `company_inn` · в симуляторе нет компании с таким ИНН · у банка нет кредитного здоровья |
| `FEATURE_OFF` | умная функция выключена флагом `FEATURE_K1…K4` — основа работает без неё |
| `USER_NOT_FOUND` | вход по ID: такого пользователя нет — выбрать из `GET v1/sandbox/personas` или создать свою компанию |
| `COMPANY_NOT_LOADED` | банк ещё собирает данные компании — повторить через пару секунд |
| `INVALID_STATUS`, `INVALID_TRANSITION`, `CANNOT_WITHDRAW` | действие недоступно в текущем статусе |
| `BKI_PENDING`, `SOURCE_WAIT` | подпись после проверки КИ · ждём свежую выписку реестра |
| `NOT_FOUND`, `APPLICATION_NOT_FOUND`, `PERSONA_NOT_FOUND` | нет такого ресурса |
| `INN_INVALID`, `INN_TAKEN`, `PERSONA_INVALID`, `FLAG_UNKNOWN`, `FLAG_NOT_APPLICABLE`, `SOURCE_UNKNOWN`, `EVENT_NOT_APPLICABLE`, `COMPANY_NOT_IN_WORLD` | ручки симулятора: неверная контрольная цифра ИНН (в ответе `suggested_inn` — ближайший верный) · ИНН занят · такой компании не бывает (`errors[]`) · нет такого флага · флаг не для этой формы (`liquidation` у ИП) · нет такого источника · событие к компании не применимо · компании нет в мире |

## Экраны → ручки
| Экран | Ручка | Что в `data` |
|---|---|---|
| «Кто вы» `/sandbox` | `GET v1/sandbox/personas?lang=ru` | массив карточек `SandboxPersonaDto` + `inn`, `role`, `person_inn`, `company_inn`, `companies`, `faults`, `custom` |
| кнопка «Войти как …» | `POST v1/sandbox/personas/{id}/login` | `token`, `persona`, `actor {kind, inn, name}`, `companies` с правами, `loading` |
| Главная страница (лендинг) | `GET v1/catalog/products?lang=ru\|en` — без входа | карточки продуктов: `name`, `benefits`, `amount_min/max`, `term_months_min/max`, `rate_from` и `rate_parts` (ключевая + отрасль + риск класса A), `decision` (`auto` · `specialist`) с текстом, `goals`; суммы — числами |
| Гид по сценариям ролей | `GET v1/sandbox/scenarios?lang=ru\|en` | сценарии: `title`, `about`, `company`, `users`, `steps[] {n, user, title, button, api {method, path, body}, expect_status, expect_http, note}` — кем войти и что нажать на каждом шаге |
| Вход по ID | `POST v1/auth/login {"login"}` · `POST v1/auth/logout` | то же, что вход карточкой: `token`, `persona`, `actor`, `companies`, `loading` |
| «Своя компания» | `GET v1/sandbox/persona-options?lang=ru` · `POST v1/sandbox/personas` | каталог: формы, параметры с границами, флаги с текстом эффекта · карточка; принимает поля конструктора как есть, `inn` (проверяется), параметры компании (`form`, `okved`, `inflow_avg`…) и `flags` — по желанию |
| Главная `/` | `GET v1/dashboard[?company_inn=]` | `total_balance`, `monthly_income`, `monthly_expenses`, `active_loans_count` (как в `DashboardStatisticsDto`), `cash_flow[6] {month, income, expenses}`, `recent_transactions[] {id, date, title, amount, direction, category}` (расход — отрицательный), `offer` — предодобрено в 1 клик |
| шапка: компания, права | `GET v1/me` · `PUT v1/me/company {inn}` | персона, `companies[] {inn, name, segment, roles, can {view, prepare, sign, approve}, why[]}`, `active_company_inn` |
| Кабинет компании | `GET v1/demo-personas/{inn}` · `GET v1/demo-personas/{inn}/dashboard/summary` | кто работает в кабинете (`DemoPersonaDto` + `user_id`, `role`) · карточки остатка, списаний и поступлений до даты разрыва (`DashboardSummaryCardDto[]`) |
| Прогноз и предложение (K1, K2, K5) | `GET v1/companies/{inn}/insights` | `cash_forecast {status CASH_GAP\|HEALTHY, horizon_days, points[], cash_gap {date, amount, first_negative_date}, operations[], daily_inflow, regular_outflows[]}`, `offer` — продукт, закрывающий разрыв; `contract` — сигнал K5: госконтракт в ЕИС и кредит на исполнение |
| Подбор кредита | `GET v1/companies/{inn}/products` | `CreditProductDto[]`: `id, name, amount, currency, rate, is_rate_from, term_months, benefits[], is_preliminary, is_recommended` + `product`, `label`, `payment`, `conditions` |
| Как гасить (K4) | `GET v1/companies/{inn}/repayment?amount=&term_months=&rate=` | `fixed` (платёж, переплата, доля поступлений трёх худших месяцев, `comfortable`), `from_inflows` (доля, минимум, за сколько месяцев уйдёт долг, переплата), `recommendation` и `why` |
| Кредитное здоровье | `GET v1/companies/{inn}/score?lang=ru` | `score`, `pd`, `class`, `contributions[]` — `title` (название фактора), `points`, `effect` (`plus · neutral · minus · unknown`), `text` — причина, только если фактор снижает балл; `levers[]` — до какого значения подтянуть фактор и сколько баллов это даст |
| Профиль компании | `GET v1/companies/{inn}/profile` | `CompanyProfileDto` + `msp_category`, `headcount`, `facts`, `source_details` (откуда и когда каждый факт) |
| Заявки и задачи на главной | `GET v1/companies/{inn}/applications/summary` · `GET v1/tasks` | заявки с укрупнённым статусом (`status_detail` — точный), задачи `SIGNATURE · DOCUMENT_REQUEST` (+ `all_tasks`) · входящие пользователя по всем компаниям |
| Заявки | `GET v1/applications[?company_inn=]` · `POST v1/applications` · `GET v1/applications/{id}` | заявка: `status`, `flags`, `request`, `decision`, `offer`, `offers` (варианты), `info_request`, `signatures`, `loan`, `deadline`, **`available_actions`** |
| Кнопки заявки | `POST v1/applications/{id}/` + `submit` · `withdraw` · `offer/accept {variant}` · `offer/decline` · `signatures` · `info-requests/answer` · `approvals/vote {vote}` | обновлённая заявка |
| Живой таймлайн | `GET v1/applications/{id}/stream` (`EventSource`) | Server-Sent Events: первым `snapshot` (статус, флаги, срок), дальше каждая запись истории (`event` — тип, `id` — номер); поток закрывается в конце заявки; переподключение — заголовок `Last-Event-ID`. Через nginx стенда буферизация выключена (`X-Accel-Buffering: no`) |
| «Почему так» | `GET v1/applications/{id}/explain` | `reasons`, `scoring {score, pd, risk_class, factors[] с интервалами карты и следующим порогом}`, `price {key_rate, industry, risk, parts[]}`, `limit {caps[], binding}`, `path_to_approval {changeable, options[]}` |
| Кредитный специалист | `GET v1/bank/queue` · `GET v1/bank/applications/{id}/dossier` · `POST v1/bank/applications/{id}/decision {action, amount?, term_months?, comment?, asks?}` | очередь с причинами, SLA, `pending_decision` · досье · заявка после решения |
| Риск-менеджер | `POST v1/bank/applications/{id}/decision/confirm {approve, comment?}` | второй ключ: одобрение специалиста выше его порога подтверждено (→ `OFFERED`) или возвращено |
| Метрики конвейера | `GET v1/bank/metrics` (только банк) | `applications`, `by_status`, `decisions {auto, manual, stp_share}`, `time_to_decision` и `manual_review` (`count`, `p50`, `p95`, `target`, `within_target`), `outcomes`, `issued {count, amount}`, `sla_breaches` |
| Проверка журнала аудита | `GET v1/bank/audit` (только банк) | `events`, `intact`, `broken_at` — номер первой записи, где цепочка хэшей не сходится, `last_hash` |
| Рабочее место по ИНН банка | те же ручки кабинета с `7701000097` | карточки главной — на рассмотрении, ждут второго ключа, выдано сегодня; `applications/summary` — очередь; `insights` — без прогноза, `products` — пусто; клиенту — 403 `BANK_ONLY` |

Кнопки рисуются по `available_actions`: `submit`, `withdraw`, `accept_offer`, `decline_offer`, `answer_info`, `sign`, у участника ООО — `vote`,
у специалиста — `decide`, у риск-менеджера — `confirm`. Права, роль и статус уже учтены — фронту не нужно повторять правила.
Матрица «статус × роль» и сценарии с перелогином — [`../15_roles.md`](../15_roles.md).

## Переход фронта с моков на API

Сервисы фронта уже ходят в эти пути — достаточно убрать `adapter: …MockAdapter` в `src/app/services/*`. Формы ответов совпадают с DTO
фронта, это проверяют сквозные тесты (`tests/e2e/test_cabinet.py`, `test_session.py`). Отличия и то, что есть сверх моков:

| Сервис фронта | Ручка | Что учесть |
|---|---|---|
| `sandboxService.fetchPersonas` | `GET v1/sandbox/personas?lang=` | сверх DTO: `role`, `person_inn`, `company_inn`, `companies`, `faults`, `custom`; есть `r12`, `risk` и люди мира `u-*` |
| `sandboxService.createPersona` | `POST v1/sandbox/personas` | тело как есть; ИНН проверяется: 422 `INN_INVALID` с `suggested_inn`, 409 `INN_TAKEN`; можно добавить `flags` из `GET v1/sandbox/persona-options` |
| `demoPersonaService` | `GET v1/demo-personas/{inn}` | сверх DTO: `user_id`, `role`, `person_inn`; ИНН банка `7701000097` — сотрудник |
| `dashboardService` | `GET v1/demo-personas/{inn}/dashboard/summary` | у ИНН банка — карточки рабочего места: на рассмотрении, второй ключ, выдано сегодня |
| `companyInsightsService` | `GET v1/companies/{inn}/insights` | сверх DTO: `offer` (предложение под разрыв), `contract` (K5), в прогнозе — `daily_inflow`, `regular_outflows` |
| `companyProductsService` | `GET v1/companies/{inn}/products` | сверх DTO: `product`, `label`, `payment`, `conditions` |
| `companyProfileService` | `GET v1/companies/{inn}/profile` | сверх DTO: `name`, `msp_category`, `headcount`, `facts`, `source_details` |
| `applicationsService` | `GET v1/companies/{inn}/applications/summary` | сверх DTO: `status_detail` (точный статус), `flags`, `all_tasks`; у ИНН банка — очередь |

Пока данные компании собираются, ручки кабинета отвечают 409 `COMPANY_NOT_LOADED` — повторить через пару секунд. Без токена кабинет
по ИНН открывается от пользователя этой компании, поэтому вход картой и переход в `/cabinet/:inn` работают без доработок. Для
разделов «Кредиты» и «Заявки»: `GET v1/applications?company_inn=`, `GET v1/applications/{id}` с `available_actions`, кнопки — ручки
заявки выше, живой таймлайн — `GET v1/applications/{id}/stream`, гид по сценариям ролей — `GET v1/sandbox/scenarios`.

## Статусы и флаги
`DRAFT → SUBMITTED → CHECKING → OFFERED | INFO_REQUESTED | UNDER_REVIEW | REJECTED`, дальше `SIGNING → SIGNED → DISBURSING → ISSUED`;
конец — `ISSUED · REJECTED · DECLINED · WITHDRAWN · EXPIRED`. Таблица переходов — `backend/app/domain/state.py`, диаграмма — [`../diagrams/application_state.md`](../diagrams/application_state.md),
все пути с тем, кто их запускает, — [`../test-scenarios.md`](../test-scenarios.md). Флаги — бейджи, не статусы: `PROVISIONAL` (условия
предварительные, подпись после КИ), `SOURCE_WAIT`, `DEGRADED_DATA`, `RECHECK`, `SLA_BREACH`, `DISBURSE_ERROR`. `deadline.at` — до когда действует статус.

## Пример: карточка персоны и заявка с офертой
```json
{"data": {"id": "s7", "code": "S7", "kind": "client", "full_name": "Анна Смирнова",
          "organization": "ИП Смирнова А. С. · подача напитков", "scenario": "Кассовый разрыв в кофейне",
          "permissions": "Все права, подписывает без доверенности", "profile": "Поступления ≈ 1,5 млн ₽ в месяц, бизнесу 2 года",
          "registries": "Все источники отвечают", "preview": "Предодобренный овердрафт …", "login_label": "Войти как Анна",
          "person_inn": "770100000079", "company_inn": "770100000079"}}
```
```json
{"data": {"id": "…", "status": "OFFERED", "flags": [], "available_actions": ["accept_offer", "decline_offer", "withdraw"],
          "offer": {"product": "OVERDRAFT", "amount": "400000.00", "term_months": 12, "payment": "5666.67",
                    "rate": {"total": "17.0", "key_rate": "14.00", "industry": "0.0", "risk": "3.0", "risk_class": "B"}},
          "deadline": {"status": "OFFERED", "at": "2026-10-21T12:10:00+00:00", "then": "EXPIRED"}}}
```

## Симулятор (только `DEMO_MODE`)
Отказ источника — `POST v1/sandbox/faults {source, mode, inn?}` (`source`: ключ из `backend/policy/sources.yaml` или `abs`; `mode`: `timeout ·
error503 · reset · garbage · empty`), событие мира — `POST v1/sandbox/events {type, inn, amount?}`, часы — `POST v1/sandbox/clock
{advance_s}`, пауза воркера — `POST v1/sandbox/worker/pause`, сброс — `POST v1/sandbox/reset`. Ничего не перезапускается.
