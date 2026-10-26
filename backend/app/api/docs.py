"""Тексты и доводка OpenAPI: введение для Swagger (/api/docs) и ReDoc (/api/redoc), разделы, ошибки RFC 9457."""

DESCRIPTION = """
Кредитный конвейер для малого бизнеса: кабинет предпринимателя и рабочее место банка в одном процессе — от потребности
до выдачи денег. Внешние системы (ЕГРЮЛ и ЕГРИП, ФНС, ГИР БО, БКИ, ЕИС, банк) смоделированы в форматах первоисточников;
все компании и люди вымышленные.

## Быстрый старт
0. **Без входа.** `GET /api/v1/catalog/products` — продукты для главной страницы: ставка «от» из ключевой ставки и спредов,
   сумма, срок, кто решает.
1. **Войти.** `POST /api/v1/auth/login` с телом `{"login": "s7"}` — ID пользователя, его ИНН или ИНН компании.
   Готовые пользователи — `GET /api/v1/sandbox/personas`.
2. **Authorize.** Вставьте `data.token` из ответа. Без токена запросы идут от последнего вошедшего пользователя,
   а ручки компании `/companies/{inn}/…` — от пользователя этой компании.
3. **Кабинет.** `GET /api/v1/companies/770100000079/insights` — прогноз остатка и кассовый разрыв 28.10;
   `…/products` — предодобренные продукты; `…/score` — кредитное здоровье с рычагами; `…/repayment?amount=400000` —
   фиксированный график или доля поступлений (K4).
4. **Заявка.** `POST /api/v1/applications` → `POST …/{id}/submit` → через пару секунд `GET …/{id}` вернёт `OFFERED` →
   `POST …/{id}/offer/accept` → `POST …/{id}/signatures` → выдача, статус `ISSUED`. «Почему так» — `GET …/{id}/explain`,
   живой таймлайн — `GET …/{id}/stream` (Server-Sent Events).
5. **Банк.** Войдите как `bank` (кредитный специалист) или `risk` (риск-менеджер): `GET /api/v1/bank/queue`, досье,
   решение, второй ключ; `GET /api/v1/bank/metrics` — доля решений без специалиста и время решения против целей SLA.

## Пользователи
| ID | Кто | Что показывает |
|---|---|---|
| `s7` | ИП Смирнова, кофейня | кассовый разрыв, предложение в 1 клик, выдача |
| `s3` | ООО «Вектор-Трейд» | встречное предложение: нагрузка не позволяет всю сумму |
| `s2` | ООО «Мастер-Строй» | крупная сделка и голосование участников (`u-li`, `u-morozov`) |
| `s4` | ООО «Ромашка-Сервис» | отказ из-за недоимки и путь к одобрению |
| `s5` | ООО «Северный Хлеб» | сумма выше порога автоматического решения: досье и решение кредитного специалиста |
| `r8` | Иван Иванов, три компании | разные права в каждой: подпись, подготовка, просмотр |
| `s8` | ООО «Код и Облако» | продукт не для отрасли — банк предлагает экспресс-кредит под ту же цель |
| `agro` | ООО «Зелёное Поле» | сезонный кредит: лимит от годовых поступлений, погашение после урожая |
| `r12` | ООО «Лента-Опт» | смена директора во время подписи; новый директор — `u-novikova` |
| `u-kuznetsova` | ООО «Вектор-Трейд» | подпись по доверенности (МЧД); после отзыва МЧД — подписывает директор `s3` |
| `n1`, `n2` | БКИ не отвечает | предварительная оферта и ручное рассмотрение |
| `bank`, `risk` | Fino Банк | очередь, досье, решения до 15 млн ₽, второй ключ выше |

`r8`, `n1`, `n2` в списке входа не показываются — вход по ID. Пошаговый гид по сценариям со сменой ролей —
`GET /api/v1/sandbox/scenarios`: кем войти, что нажать, какой статус ждать.
Своя компания с флагами (недоимка, просрочка, крупная сделка, БКИ не отвечает…) — `POST /api/v1/sandbox/personas`,
каталог флагов и параметров — `GET /api/v1/sandbox/persona-options`.

## Статусы заявки
`DRAFT → SUBMITTED → CHECKING → OFFERED | INFO_REQUESTED | UNDER_REVIEW | REJECTED → SIGNING → SIGNED → DISBURSING → ISSUED`.
Конец — `ISSUED`, `REJECTED`, `DECLINED`, `WITHDRAWN`, `EXPIRED`. Флаги — бейджи, а не статусы: `PROVISIONAL`, `RECHECK`,
`SOURCE_WAIT`, `SLA_BREACH`, `DEGRADED_DATA`, `DISBURSE_ERROR`. Кнопки текущего пользователя — `available_actions` заявки.

## Соглашения
- Успех — `{"data": …}`; ошибка — RFC 9457 `application/problem+json` с машинным `code`: ветвиться по нему, `detail` — для людей.
- Поля — snake_case, даты — ISO 8601. Деньги в ядре — строкой (`"400000.00"`, без потерь), в витрине кабинета — числами.
- `X-Request-Id` у каждого ответа (можно прислать свой); подача заявки принимает `Idempotency-Key`.
- Решение объяснимо: причины с правилом или нормой, вклад факторов скоринга, ставка из частей (ключевая + отрасль + риск).
"""

TAGS = [
    {"name": "auth", "description": "Вход по ID и выход. Токен из ответа — в **Authorize**."},
    {"name": "me", "description": "Кто я, мои компании и права. Права считаются из ЕГРЮЛ/ЕГРИП и договора ДБО на каждый запрос; "
                                  "входящие задачи по всем компаниям."},
    {"name": "cabinet", "description": "Кабинет компании по ИНН в контракте фронта (суммы — числами): прогноз остатка и кассовый "
                                       "разрыв (K1), предодобренные продукты и подбор от задачи (K2), кредитное здоровье "
                                       "с рычагами (K3), график погашения или доля поступлений (K4), профиль, заявки "
                                       "и задачи. ИНН банка открывает рабочее место сотрудника."},
    {"name": "company", "description": "Данные компании: права с основаниями, обновление из реестров, главная."},
    {"name": "catalog", "description": "Продукты, цели и отрасли; ставка из частей; калькулятор платежа и графика."},
    {"name": "application", "description": "Заявка от черновика до выдачи: подача, оферта и её варианты, подпись, ответ "
                                           "на запрос банка, голосование участников, отзыв, «почему так»."},
    {"name": "bank", "description": "Рабочее место банка: очередь исключений, досье, решение специалиста в пределах полномочий, "
                                    "второй ключ риск-менеджера выше них (принцип четырёх глаз)."},
    {"name": "simulator", "description": "Мир симулятора: пользователи, своя компания с флагами, события в реестрах, отказы "
                                         "источников, часы, сброс. Работает при `DEMO_MODE=true`."},
    {"name": "system", "description": "Здоровье сервиса."},
]

SERVERS = [
    {"url": "/", "description": "тот же адрес, откуда открыта документация"},
    {"url": "http://localhost:8000", "description": "API напрямую, локально (порт по умолчанию, API_PORT)"},
    {"url": "http://localhost:8080", "description": "стенд: через nginx фронта (порт по умолчанию, WEB_PORT)"},
]

TAG_GROUPS = [   # группы разделов в ReDoc
    {"name": "Клиент", "tags": ["auth", "me", "cabinet", "company", "catalog", "application"]},
    {"name": "Банк", "tags": ["bank"]},
    {"name": "Симулятор и сервис", "tags": ["simulator", "system"]},
]

SWAGGER = {"docExpansion": "none", "defaultModelsExpandDepth": 0, "persistAuthorization": True,
           "displayRequestDuration": True, "filter": True, "tryItOutEnabled": True}


def customize(schema: dict) -> dict:
    """Ошибки — application/problem+json со схемой ProblemDetails (и у 422 от валидации FastAPI); группы разделов для ReDoc."""
    problem = {"$ref": "#/components/schemas/ProblemDetails"}
    for path in schema.get("paths", {}).values():
        for operation in path.values():
            for code, response in operation.get("responses", {}).items():
                if not code.startswith(("4", "5")):
                    continue
                content = response.get("content", {})
                body = next((v for v in content.values() if v.get("schema", {}).get("$ref", "").endswith("/ProblemDetails")),
                            None) or content.get("application/json") or {}
                if body.get("schema", {}).get("$ref", "").endswith("/HTTPValidationError") or not body:
                    body = {"schema": problem}
                response["content"] = {"application/problem+json": body}     # ошибка — всегда RFC 9457, даже у потока
                if code == "422" and response.get("description") == "Validation Error":
                    response["description"] = "Ошибка в данных запроса (VALIDATION_ERROR с errors[])"
        for operation in path.values():
            operation.setdefault("security", [])                 # без замка — ручка доступна без входа
    components = schema.get("components", {}).get("schemas", {})
    for name in ("HTTPValidationError", "ValidationError"):
        components.pop(name, None)
    schema["servers"] = SERVERS
    schema["x-tagGroups"] = TAG_GROUPS
    return schema
