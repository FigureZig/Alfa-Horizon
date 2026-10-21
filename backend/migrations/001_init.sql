-- 5 таблиц (docs/06 §4). Всё остальное вычисляется или лежит в policy/*.yaml.

CREATE TABLE applications (
    id           uuid PRIMARY KEY,
    company_inn  text        NOT NULL,
    status       text        NOT NULL,
    flags        text[]      NOT NULL DEFAULT '{}',
    data         jsonb       NOT NULL DEFAULT '{}'::jsonb,   -- запрос, решение, оферта, подписи, выдача
    version      int         NOT NULL DEFAULT 0,             -- оптимистическая блокировка
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX applications_company_idx ON applications (company_inn);
CREATE INDEX applications_status_idx ON applications (status);

-- История и аудит: только добавление; хэш-цепочка показывает подмену записи (docs/10 P19).
CREATE TABLE events (
    id               bigserial   PRIMARY KEY,
    at               timestamptz NOT NULL DEFAULT now(),
    application_id   uuid        REFERENCES applications (id),
    type             text        NOT NULL,
    actor            text        NOT NULL,
    payload          jsonb       NOT NULL DEFAULT '{}'::jsonb,
    idempotency_key  text        UNIQUE,
    prev_hash        text,
    hash             text        NOT NULL
);
CREATE INDEX events_application_idx ON events (application_id, id);

CREATE FUNCTION events_notify() RETURNS trigger AS $$
BEGIN
    PERFORM pg_notify('events', json_build_object('id', NEW.id, 'application_id', NEW.application_id, 'type', NEW.type)::text);
    RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER events_notify AFTER INSERT ON events FOR EACH ROW EXECUTE FUNCTION events_notify();

-- Очередь и таймеры: шаги конвейера, ретраи, дедлайны, выдача. Статусы — docs/diagrams/application_state.md §2.
CREATE TABLE jobs (
    id              bigserial   PRIMARY KEY,
    kind            text        NOT NULL,
    application_id  uuid        REFERENCES applications (id),
    payload         jsonb       NOT NULL DEFAULT '{}'::jsonb,
    status          text        NOT NULL DEFAULT 'PENDING',
    attempts        int         NOT NULL DEFAULT 0,
    run_at          timestamptz NOT NULL DEFAULT now(),
    lease_until     timestamptz,
    last_error      text,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX jobs_ready_idx ON jobs (status, run_at);

-- Ответы реестров и банка с происхождением: API читает только их, поэтому экран живёт, когда реестр лежит.
CREATE TABLE snapshots (
    source      text        NOT NULL,
    key         text        NOT NULL,
    payload     jsonb,
    status      text        NOT NULL,        -- ok · not_found · error
    error       text,
    fetched_at  timestamptz NOT NULL DEFAULT now(),
    hash        text,
    PRIMARY KEY (source, key)
);

-- Операционные мелочи: breaker по источникам, персона демо, часы песочницы, пауза воркера.
CREATE TABLE kv (
    key         text        PRIMARY KEY,
    value       jsonb       NOT NULL,
    updated_at  timestamptz NOT NULL DEFAULT now()
);
