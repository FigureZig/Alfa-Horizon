# Модель данных

Сгенерировано из кода: `cd backend && uv run python -m qa.er`. Физическая модель — из `backend/migrations/*.sql`, логическая — из схем ответов API `backend/app/api/schemas.py`. Почему так мало таблиц — `06_architecture.md` §4.

## 1. Таблицы PostgreSQL

- `applications` — заявка целиком
- `events` — история и аудит, только добавление
- `jobs` — очередь задач worker и таймеры
- `snapshots` — ответы реестров и банка с происхождением
- `kv` — операционные мелочи

Компания и человек — не таблицы: их данные приходят из реестров и банка и лежат в `snapshots` (ключ — ИНН), права считаются на лету. Продукты, правила и скоринг — `policy/*.yaml`, версия политики пишется в каждое решение.

```mermaid
erDiagram
    applications |o--o{ events : "application_id"
    applications |o--o{ jobs : "application_id"
    applications {
        uuid id PK
        text company_inn
        text status
        text_array flags
        jsonb data "запрос, решение, оферта, подписи, выдача"
        int version "оптимистическая блокировка"
        timestamptz created_at
        timestamptz updated_at
    }
    events {
        bigserial id PK
        timestamptz at
        uuid application_id FK
        text type
        text actor
        jsonb payload
        text idempotency_key UK
        text prev_hash
        text hash
    }
    jobs {
        bigserial id PK
        text kind
        uuid application_id FK
        jsonb payload
        text status
        int attempts
        timestamptz run_at
        timestamptz lease_until
        text last_error
        timestamptz created_at
    }
    snapshots {
        text source PK
        text key PK
        jsonb payload
        text status "ok · not_found · error"
        text error
        timestamptz fetched_at
        text hash
    }
    kv {
        text key PK
        jsonb value
        timestamptz updated_at
    }
```

## 2. Заявка как документ (`applications.data`)

Запрос, решение движка с причинами и скорингом, оферта и варианты, подписи, согласие участников, решения банка и выдача хранятся одним документом заявки: читаются вместе, меняются в одной транзакции с событием в `events`. Те же поля отдаёт `GET /api/v1/applications/{id}` (схема `ApplicationView` в Swagger и ReDoc).

```mermaid
erDiagram
    ApplicationView ||--o| Decision : "decision"
    ApplicationView ||--o| Offer : "offer"
    ApplicationView ||--o{ Offer : "offers"
    ApplicationView ||--o| InfoRequest : "info_request"
    ApplicationView ||--o| Signers : "signers"
    ApplicationView ||--o{ Signature : "signatures"
    ApplicationView ||--o| Approval : "approval"
    ApplicationView ||--o| BankNote : "pending_decision"
    ApplicationView ||--o| BankNote : "bank_decision"
    ApplicationView ||--o| Loan : "loan"
    ApplicationView ||--o| Deadline : "deadline"
    Decision ||--o| Offer : "offer"
    Decision ||--o{ Offer : "alternatives"
    Decision ||--o{ Reason : "reasons"
    Decision ||--o| Risk : "risk"
    Offer ||--|| Rate : "rate"
    Approval ||--o{ Participant : "participants"
    Approval ||--o{ Vote : "votes"
    BankNote ||--o| Offer : "offer"
    Risk ||--o{ Contribution : "contributions"
    ApplicationView {
        str id
        str company_inn
        enum status
        list flags
        int version
        str created_at
        str updated_at
        json request
        bool consent_bki
        json created_by
        json final_check
        str sla_until
        list available_actions
    }
    Decision {
        enum outcome
        str status
        enum offer_kind
        list counter
        list conditions
        list asks
        list caps
        list hints
        list flags
        list trace
        str policy_version
        str mode
        str kind
    }
    Offer {
        enum product
        str product_name
        str amount
        int term_months
        str payment
        str repayment
        str binding_cap
        int variant
    }
    InfoRequest {
        list asks
        str from
        str comment
    }
    Signers {
        str mode
        list any_of
        list required
    }
    Signature {
        str inn
        str fio
        str role
        str at
    }
    Approval {
        str status
        str method
        float for_pct
        float against_pct
        float threshold_pct
    }
    BankNote {
        str at
        str by
        str action
        str comment
        int limit
        json second_key
    }
    Loan {
        str loan_id
        str amount
        str rate
        int term_months
        str status
        str disbursed_at
    }
    Deadline {
        enum status
        str at
        enum then
    }
    Reason {
        str code
        str kind
        str text
    }
    Risk {
        int score
        float pd
        enum class
        enum best_class
        list missing
        list weak
    }
    Rate {
        str total
        str key_rate
        str industry
        str risk
        enum risk_class
        str section
        str bucket
        str security
    }
    Participant {
        str inn
        str fio
        float share
    }
    Vote {
        str inn
        str fio
        enum vote
    }
    Contribution {
        str factor
        any value
        int points
        str reason
        enum effect
    }
```
