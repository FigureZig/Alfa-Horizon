# 1. Бэкенд: что поменялось и где править фронт

Читать первым. Файл 2 — экраны и путь пользователя, файл 3 — дизайн.

- **Бэк:** ветка `feat/product-polish`, PR в `main`. Пока PR не смёржен, свою ветку фронта делайте от неё.
- **Контракт:** `docs/api/openapi.json`. Живой Swagger — http://localhost:8000/api/docs. Соглашения: ошибки, деньги, `?lang=` — в `docs/api/README.md`.
- **Стенд:** `cd infra && docker compose up --build` → фронт :8080, API :8000. Для `pnpm dev`: `VITE_API_BASE_URL=http://localhost:8000/api`.
- **Сброс мира:** `POST /api/v1/sandbox/reset`. Выданные до сброса кредиты перестают учитываться, история заявок остаётся.

Пути к файлам ниже — от `frontend/src/app/`.

## 1. Что сломалось на нынешнем фронте — чинить первым

| # | Что изменилось на бэке | Что видно сейчас | Где править |
|---|---|---|---|
| 1 | Конструктор: `inflow_cv`, `inflow_trend`, `debt_load`, `overdue_days`, `bki_requests`, `tax_debt`, `participants`, `profit_margin` стали необязательными. В `GET /sandbox/persona-options` у них `params[].default: null` — бэк выведет их из простых ответов | создание своей компании падает: «Persona form number is required» | `mappers/sandbox.mapper.ts` (`toRequiredNumber`) — слать только то, что человек заполнил. Сам экран переделать на простые вопросы (файл 2, «Своя компания») |
| 2 | Участник ООО без доступа в интернет-банк больше не видит счёт компании: `insights`, `products`, `profile`, `score`, `dashboard/summary`, `GET /applications` отвечают 403 `FORBIDDEN` | после входа участника — ошибки загрузки | ответ входа и `GET /me` → `companies[].can`. При `view: false` и `approve: true` вести на экран «Голосование» (файл 2) |
| 3 | Калькулятор овердрафта (`POST /calc/loan`, `repayment: revolving`): `overpayment: null`, `schedule: []`, новое `usage_example {amount, days, interest, text}` | «Переплата 0 ₽» | `mappers/loan-calc.mapper.ts:20` (`Number(null)` = 0), `features/credits/components/LoanCalculator.vue:293` — для овердрафта показывать `usage_example.text` |
| 4 | `GET /companies/{inn}/repayment?…&product=` для овердрафта и кредитов с погашением в конце срока → 422 `REPAYMENT_NOT_APPLICABLE` | — | `RepaymentComparison.vue`: звать только для `repayment: "annuity"`, параметр `product` передавать |
| 5 | `cash_forecast.status` теперь бывает и `COVERED`: минус в пределах подключённого овердрафта. Рядом поле `credit_line` | на графике минус, а текст «всё в порядке» | `types/company/cash-forecast-status-enum.ts`, `composables/useCashForecast.ts`, `features/dashboard/components/CashForecastCard.vue` |
| 6 | Источник данных у ИП — `EGRIP`, у ООО и АО — `EGRUL` | сырой ключ `companyInsights.source.EGRIP` | `types/company/data-source-enum.ts`, `i18n/locales/ru.ts` (`source.EGRIP: 'ЕГРИП'`), то же в `en.ts` |
| 7 | Сроки как в бою: оферта — 10 дней, дозапрос и голосование — 7, подпись — 5, ручное рассмотрение — 4 часа (раньше 5–15 минут) | — | везде, где показан `deadline.at`: «осталось 9 дней», а не минуты |
| 8 | Карточки входа: новые поля `badge`, `role_title`, `about`. Старые `code`, `scenario`, `preview` теперь их копии. `n1`, `n2`, `r8` убраны из списка и входят только по ID; появился `u-kotov` | вместо «S7» — «ИП», вместо сценария — должность | `mappers/sandbox.mapper.ts`, `features/sandbox/components/SandboxPersonaCard.vue` — перейти на новые поля |
| 9 | «Сегодня» — по часам мира: `today` в `GET /demo-personas/{inn}`. `created_at`, `events.at`, `loan.disbursed_at` — тоже время мира | приветствие с датой браузера, а мир живёт 21.10.2026 | `features/dashboard/components/DashboardGreeting.vue:16` (`new Date()`) → `today` из API |

## 2. Новые данные — по экранам

| Экран | Ручка | Что взять |
|---|---|---|
| Вход | `POST /sandbox/personas/{id}/login` | в ответе уже есть `companies[] {inn, short_name, can, roles}` — по ним сразу решать, куда вести (файл 2, §1) |
| Шапка кабинета | `GET /me`, `PUT /me/company {inn}` | `companies[].short_name` для переключателя компаний (у Иванова `s5` их три) |
| Главная: остаток | `GET /demo-personas/{inn}/dashboard/summary` | у карточки `balance` есть `credit_line` — «+ овердрафт до 600 000 ₽» |
| Главная: прогноз | `GET /companies/{inn}/insights` | `cash_forecast.status` (`CASH_GAP` / `COVERED` / `HEALTHY`), `cash_gap {date, amount}`, `credit_line` |
| Главная: закрыть разрыв | то же | `offer` (продукт и лимит) и `offer.cover {amount, days, interest}` — сколько стоит закрыть разрыв: «28.10 возьмёте 36 196 ₽ на 1 день, проценты ≈ 17 ₽» |
| Главная: госконтракт | то же | `contract` — новый госконтракт в ЕИС на 18 млн ₽ и кредит на его исполнение (у Кравец, `s2`) |
| Подбор от задачи | `GET /companies/{inn}/offers?goal=&amount=&term_months=` | `options[]`: `available`, `label`, `offer {amount, term_months, rate, payment}`, `max_amount`, `needs[].text` (что понадобится), `why[]` (почему нет), `causes[] {code, kind, text}` (те же причины с кодом — для иконок), `recommended`. Стоп-факторы компании — в `blockers[] {code, text}` |
| Новая заявка | `POST /applications` | поле `product` теперь можно не передавать: банк подберёт сам по `goal`. В ответе — `request.product_chosen_by: "bank"`, а если лимит овердрафта больше нужной суммы — `request.need` |
| Заявка: кнопки | `GET /applications/{id}` | **только** `available_actions`. Кто подписал, тому кнопки `sign` больше нет. Совместная подпись: `signers {mode: joint, required[]}` минус `signatures[].inn` = кого ещё ждём. Имена по ИНН — из `GET /companies/{inn}/profile` → `facts.eio[] {inn, fio, title}` |
| Заявка: срок шага | то же | `deadline {status, at, then}` |
| Заявка: выдача | то же | `loan.kind`: `limit` → «Лимит подключён к счёту», `loan` → «Деньги зачислены». `loan.number` — номер договора `КД-2026/…` вместо UUID |
| Заявка: «почему так» | `GET /applications/{id}/explain` | `limit.caps[] {title, text, value, binding}` — суммы уже в `text`, сработавший лимит — `binding: true`. `path_to_approval {kind, title}` — заголовок по исходу: «Как получить одобрение», «…всю сумму», «Как улучшить условия» |
| Заявка: история | `GET /applications/{id}/events?lang=` и SSE `/stream` | `by {kind: client\|bank\|system, name, title, detail}`: «Елена Кравец», «Мария Соколова · Кредитный специалист», «Банк · автоматическое решение». Никаких «вы» и «движок» |
| Калькулятор | `POST /calc/loan` | у овердрафта — `usage_example.text` |
| Погашение | `GET /companies/{inn}/repayment` | `why` уже содержит экономию, отдельно — `saving` |
| Банк: все заявки | `GET /bank/applications?status=&decided_by=engine\|bank&q=` | таблица: `company_name`, `request.product`, `request.amount`, `status`, `outcome`, `decided_by`, `risk_class`, `updated_at`. `decided_by: null` — решение ещё не принято |
| Банк: досье | `GET /bank/applications/{id}/dossier` | расхождения данных теперь с именами: «руководитель по ЕГРЮЛ — Никитин С. О., в анкете банка — Фомин А. П.» |
| Своя компания: вопросы | `GET /sandbox/persona-options` | `industries[]`, `structures[] {title, means, forms}`, `people[] {title, means, forms}`, `choices {seasonality, stability, trend, channel, loans, delays}`, `flags[] {title, effect, forms}` |
| Своя компания: живой предпросмотр | `POST /sandbox/personas/preview` (тело — как у создания; при правке `?persona_id=`) | **новое.** Ничего не сохраняет, ~60 мс. `products[] {product, name, available, label, max_amount, rate, payment, why[] {code, text, fields[]}, needs[], recommended}`, `blockers[] {code, text, fields[]}`, `score {score, class, factors[] {title, effect, points, fields[]}}`, `path {structure, sign_mode, means}`, `people[] {badge, full_name, role_title}` — как они появятся на экране входа. `fields` — ответы конструктора, от которых зависит причина: `loans`, `delays`, `inflow_avg`, `industry`, `structure`, `flags.tax_debt`… Картина — как при подаче, с согласием на запрос в БКИ (`assumes: "consent_bki"`). Совпадает с кабинетом созданной компании |
| Своя компания: создать | `POST /sandbox/personas` | карточка создателя. Остальные люди компании — в `GET /sandbox/personas` по `company_inn`, у каждого свой вход |
| Своя компания: изменить | `PUT /sandbox/personas/{id}` (тело — как у создания) | **новое.** ИНН тот же, реестры, выписка и люди пересобираются: убрали бухгалтера — его входа нет. Заявки остаются и уходят на пересмотр. Только `custom` и только через создателя компании (`id` вида `c12`). Свой сотрудник банка (`b3`) — имя и должность |
| Своя компания: удалить | `DELETE /sandbox/personas/{id}` | **новое.** `deleted[]` — все её люди. Моки компании снимаются, заявки остаются в истории банка под прежним названием |
| Панель проверяющего | `GET /sandbox/scenarios` | шаги: `user` (кем войти), `button` (что нажать), `expect_status` (какой статус ждать), `title`, `note` |

## 3. Новые ошибки

Показывать `detail` с бэка — это уже человеческий текст. Не «Не удалось загрузить» с кнопкой «повторить».

| Код | Где | Что показать |
|---|---|---|
| 403 `FORBIDDEN` | ручки кабинета у участника без доступа | не ошибка — экран «Голосование» |
| 422 `GOAL_REQUIRED` | `POST /applications` без `product` и без `goal` | «На что нужны деньги?» |
| 422 `NO_PRODUCT_FOR_GOAL` | то же, если подходящего продукта нет | `blockers[].text` и `why` — что мешает и что сделать |
| 422 `REPAYMENT_NOT_APPLICABLE` | погашение для овердрафта | не звать |
| 422 `STRUCTURE_NOT_APPLICABLE` | конструктор: у ИП нет участников, директоров и доверенности; у АО — только «владелец и директор — один человек» | варианты фильтровать по `structures[].forms` и `people[].forms` заранее |
| 422 `STRUCTURE_CONFLICT` | конструктор: «один владелец» вместе с флагом «Крупная сделка, три участника» | флаг или устройство — что-то одно |
| 422 `ANSWERS_CONFLICT` | конструктор: просрочка при «Кредитов нет»; в ответе `fields` | не давать выбрать просрочку без кредита |
| 422 `INN_INVALID` | конструктор | подставить `suggested_inn` |
| 409 `PERSONA_READONLY` | `PUT` или `DELETE` готового пользователя мира | у готовых компаний нет меню «Изменить / Удалить» |
| 409 `PERSON_IN_COMPANY` | `PUT` или `DELETE` человека своей компании (`c12-p1`), в ответе `owner` | меню — только у компании (у создателя) |
| 422 `KIND_CHANGE`, `FORM_CHANGE` | правка: клиента не сделать сотрудником банка, ООО — ИП (другой ИНН) | форму у ООО/АО ↔ ИП в правке не давать менять |

## 4. На что можно опираться

- **Права и кнопки считает бэк:** роль человека в компании, доли, совместная подпись, доверенность. Фронт ничего не вычисляет — рисует `available_actions` и `GET /me → companies[].can`.
- **Время одно:** часы мира. «Сегодня», сроки и история — из API, без `new Date()`.
- **Выданный кредит сразу виден:** прогноз переходит в `COVERED`, подключённый овердрафт второй раз не предлагается, лимиты считаются с учётом платежей.
- **Ручки, которые фронт не зовёт** (`/dashboard`, `/catalog`, `/tasks`, `/auth/login` и др.), живы: на них опираются Swagger, Postman и тесты.
