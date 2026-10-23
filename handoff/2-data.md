# Откуда брать данные

Справочник к `1-redesign.md`: для каждого компонента и экрана — ручка и поля.

- **Полный контракт:** `docs/api/openapi.json`, живой Swagger — http://localhost:8000/api/docs.
- **Стенд:** `cd infra && docker compose up --build` → фронт :8080, API :8000.
- **Пути** ниже — от `/api/v1`.

## Правила, на которые можно опираться

- **Кнопки заявки — только из `available_actions`.** Права считает бэк: доли, совместная подпись, доверенность, ДБО. Фронт ничего не вычисляет.
- **«Сегодня» — только из API** (`today` в `GET /demo-personas/{inn}`): у мира свои часы.
- **Мир живёт до сброса.** События реестров и отказы источников перелогин не снимает; снимает `POST /sandbox/reset`.
- **Ошибки отдают `detail` по-человечески** — показывать его, а не «не удалось загрузить».

## Компоненты

| Компонент | Ручка | Поля |
|---|---|---|
| `StatusHeader` | `GET /applications/{id}` | `status`, `flags` (`PROVISIONAL`, `RECHECK`, `SLA_BREACH`, `DISBURSE_ERROR`), `available_actions`, `deadline {status, at, then}`, `signers {mode, required, any_of}`, `signatures[]`, `approval {status, method, participants[], votes[]}`, `request`, `offer`, `loan`, `info_request`, `sla_until` |
| — кто я | `GET /me` | `companies[] {inn, short_name, can {view, prepare, sign, approve}, roles}` |
| — имена подписантов | `GET /companies/{inn}/profile` | `facts.eio[] {inn, fio, title}` — сопоставить с `signers.required` / `any_of` |
| `WhyCard` | `GET /applications/{id}/explain?lang=ru` | уровень 1 — `path_to_approval {kind, title, options[] {title, levers, outcome, amount, rate}}`; уровень 2 — `reasons[]`, `limit {amount, binding, caps[] {title, text, value, binding}}`; уровень 3 — `scoring {score, risk_class, factors[] {title, effect, points, text}, missing}`, `price {total, parts[]}` |
| `OfferChooser` | `GET /applications/{id}` | `offers[] {product_name, amount, term_months, rate, payment, repayment}`; что просили — `request {amount, term_months}`; принять — `POST /applications/{id}/offer/accept {variant}` |
| `TaskBanner` | `GET /companies/{inn}/applications/summary?lang=ru` | `tasks[] {type, title, due_date, application_id}` |
| `Timeline` | `GET /applications/{id}/events?lang=ru` (и поток `GET /applications/{id}/stream`) | `type`, `at`, `payload` (у смены статуса — `from`, `to`, `reason`), `by {kind client\|bank\|system, name, title, detail}` |
| `WorldChangedNotice` | то же | флаг `RECHECK` у заявки + `payload.reason` последнего `application.status_changed` от `by.kind = system` |

## Экраны

| Экран | Ручка | Поля |
|---|---|---|
| Главная продукта | `GET /catalog/products?lang=ru` | `products[] {name, benefits[], rate_from, amount_min, amount_max, term_months_min, term_months_max, decision_text}`, `key_rate` |
| Вход | `GET /sandbox/personas?lang=ru` | `id`, `kind`, `badge`, `full_name`, `role_title`, `about`, `company_inn`, `companies[]`, `custom` |
| — войти | `POST /sandbox/personas/{id}/login` | `token`, `companies[].can` — куда вести: банк → очередь, `view` → главная, иначе `approve` → голосование |
| — своя компания: правка и удаление | `PUT` / `DELETE /sandbox/personas/{id}` | только `custom` и только у создателя компании |
| Конструктор: вопросы | `GET /sandbox/persona-options?lang=ru` | `industries[]`, `structures[] {title, means, forms}`, `people[] {title, means, forms}`, `choices {...}`, `flags[] {title, effect, forms}`, `params[]` |
| — живой результат | `POST /sandbox/personas/preview` (тело как у создания; при правке `?persona_id=`) | `products[] {name, available, label, max_amount, rate, why[] {text, fields[]}}`, `blockers[] {text, fields[]}`, `score {score, class}`, `path {structure, sign_mode, means}`, `people[]`; `fields` — какие ответы подсветить |
| — создать | `POST /sandbox/personas` | ответ — карточка создателя; люди компании — `GET /sandbox/personas` по `company_inn` |
| Главная кабинета: деньги | `GET /companies/{inn}/insights?lang=ru` | `cash_forecast {status CASH_GAP\|COVERED\|HEALTHY, cash_gap {date, amount}, credit_line, points[], operations[]}`, `offer` + `offer.cover {amount, days, interest}`, `contract` |
| — цифры | `GET /demo-personas/{inn}/dashboard/summary?lang=ru` | карточки остатка, списаний и поступлений; у остатка `credit_line` |
| — предложения | `GET /companies/{inn}/products?lang=ru` | личные условия; пусто → `GET /companies/{inn}/offers` → `blockers[].text` |
| — что банк знает | `GET /companies/{inn}/profile?lang=ru` | `activity.title` (коротко), `sources`, `updated_at` |
| Кредиты | `GET /companies/{inn}/offers?goal=&amount=&term_months=` | `options[] {name, available, label, offer {amount, term_months, rate, payment}, max_amount, needs[].text, why[], causes[] {code, text}}`, `recommended`, `blockers[]`, `bki_known` — `false` значит прогноз без кредитной истории |
| — калькулятор | `POST /calc/loan` | у овердрафта `usage_example.text` вместо переплаты |
| Новая заявка | `POST /applications`, `POST /applications/{id}/submit` | `product` можно не передавать — банк выберет по `goal` |
| Дозапрос | `POST /applications/{id}/info-requests/answer` | `{documents[], comment}`; что просят — `info_request` |
| Голосование | `POST /applications/{id}/approvals/vote` | `{vote: for\|against}`; участнику без доступа к счёту — только заявки из `applications/summary` |
| Подпись | `POST /applications/{id}/signatures` | — |
| Банк: очередь и реестр | `GET /bank/queue`, `GET /bank/applications?status=&decided_by=&q=` | реестр: `company_name`, `status`, `outcome`, `decided_by` (`null` — ещё не решено) |
| Банк: досье | `GET /bank/applications/{id}/dossier` | причины, факты с источниками, предложение движка |
| — решение | `POST /bank/applications/{id}/decision` | `{action approve\|reject\|request_info, amount?, term_months?, comment, asks?}`; второй ключ — `POST …/decision/confirm {approve, comment}` |
| Панель «Как проверить» | `GET /sandbox/scenarios?lang=ru` | шаги: `user {id, full_name}`, `title`, `button`, `expect_status`, `note`; пустой `user` — шаг банка |
| — мир | `POST /sandbox/reset`; `GET\|POST /sandbox/clock {advance_s}`; `POST /sandbox/events {type, inn}`; `GET\|POST\|DELETE /sandbox/faults`; `POST /sandbox/worker/{pause\|resume}` | перемотка к сроку: `deadline.at` − `now` из `GET /sandbox/clock` |

## Ошибки, которые надо показать по-человечески

| Код | Где | Что показать |
|---|---|---|
| 403 `FORBIDDEN` | ручки кабинета у участника без доступа | не ошибка — экран «Голосование» |
| 422 `GOAL_REQUIRED`, `NO_PRODUCT_FOR_GOAL` | заявка без продукта | `blockers[].text` и что сделать |
| 422 `ANSWERS_CONFLICT`, `STRUCTURE_CONFLICT`, `STRUCTURE_NOT_APPLICABLE` | конструктор | подсветить поля из `fields` |
| 422 `INN_INVALID` | конструктор | подставить `suggested_inn` |
| 409 `PERSONA_READONLY`, `PERSON_IN_COMPANY` | правка или удаление | у готовых компаний и у людей компании меню нет |
| 409 `BKI_PENDING` | подпись при `PROVISIONAL` | не допускать: кнопки `sign` в этом состоянии нет |
