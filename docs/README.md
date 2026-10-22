# Документация

Как устроен кредитный кабинет и почему так. Каждая цифра и норма — со ссылкой на источник в [`10_sources.md`](10_sources.md).

| Документ | О чём |
|---|---|
| [02_product.md](02_product.md) | продукт: работы клиента, путь от потребности до выдачи, экраны, статусы, исходы решения, сценарии, скоуп |
| [03_smart.md](03_smart.md) | «умный» слой: радар кассового разрыва, предложение в 1 клик, путь к одобрению, погашение из поступлений, кредит под контракт |
| [04_decision_engine.md](04_decision_engine.md) | движок решения: факты и их свежесть, правила, поведение при неизвестных данных, контрпредложение, запись решения |
| [12_scoring.md](12_scoring.md) | скоринг: балльная карта для ИП и ООО/АО, вероятность дефолта, классы риска, как класс влияет на деньги, проверка модели |
| [13_credit_mechanics.md](13_credit_mechanics.md) | деньги: продукты по отраслям ОКВЭД, ставка из частей, лимит и контрпредложение, калькуляторы, мир компаний с исходами |
| [14_credit_landscape.md](14_credit_landscape.md) | ресёрч: какие кредитные решения бывают у бизнеса (5 правовых форм, 16 типов), что дать легко и что сложно, почему у нас шесть продуктов |
| [15_roles.md](15_roles.md) | роли и статусы: кто что может в каждом статусе, пользователи симулятора, сценарии с перелогином между ролями (собрано из кода) |
| [scoring_validation.md](scoring_validation.md) | проверка скоринга на синтетическом портфеле: Gini, KS, калибровка PD, покрытие риска ставкой, PSI, монотонность факторов (собрано из кода) |
| [05_legal.md](05_legal.md) | право: кто вправе подать и подписать, крупная сделка, согласия, доверенности, нормы закона |
| [06_architecture.md](06_architecture.md) | архитектура: компоненты, устройство кода, 5 таблиц, API, события и задачи, запуск, стек |
| [07_resilience.md](07_resilience.md) | устойчивость: поведение при отказе каждого источника, негативные сценарии N1–N17, отказы на лету без перезапуска |
| [08_simulator.md](08_simulator.md) | симулятор: вход пользователем и перелогин, своя компания, мир компаний, события мира, часы, отказы интеграций |
| [09_data_contracts.md](09_data_contracts.md) | внешние системы: ручки и поля в форматах первоисточников (ЕГРЮЛ 4.06, наборы ФНС, ГИР БО, кредитный отчёт ЦБ) |
| [10_sources.md](10_sources.md) | реестр источников: цифры, нормы и практики со ссылками и статусом проверки |
| [test-scenarios.md](test-scenarios.md) | тестовые сценарии ядра, собранные из кода: граф статусов и 16 сквозных прогонов, pairwise-персоны с исходами, стоп-факторы, инварианты |
| [diagrams/](diagrams/) | модель данных (`data_model.md`, Mermaid ER из миграций и схем API), сценарии в BPMN (`scenarios-bpmn.drawio`, PNG — `png/scenarios/`), C4 с потоками данных (`c4-data-flows.drawio`, PNG — `png/`), архитектура как код (`architecture.c4`, LikeC4), статусы заявки (`application_state.md`, Mermaid) |
| [api/openapi.json](api/openapi.json) | контракт API, выгружается из бэкенда |
| [api/README.md](api/README.md) | как фронту работать с API: конверт `{data}`, ошибки RFC 9457, вход пользователем, какие ручки за какими экранами |
| [api/postman_collection.json](api/postman_collection.json) | коллекция запросов Postman: вход, кабинет, заявка до выдачи, сценарии ролей с перелогином (собрана из кода) |

## Где что по требованиям кейса

| Требование | Где |
|---|---|
| Архитектура | [06_architecture.md](06_architecture.md), C4 в [diagrams/](diagrams/) |
| OpenAPI | [api/openapi.json](api/openapi.json) и соглашения в [api/README.md](api/README.md); живая документация — Swagger http://localhost:8000/api/docs и ReDoc http://localhost:8000/api/redoc |
| Диаграмма статусов | [diagrams/application_state.md](diagrams/application_state.md); в коде — таблица переходов `backend/app/domain/state.py` |
| Скоринг и его проверка | [12_scoring.md](12_scoring.md), отчёт на синтетике — [scoring_validation.md](scoring_validation.md) |
| Какие кредитные решения бывают у бизнеса | [14_credit_landscape.md](14_credit_landscape.md) |
| Модель данных | ER-диаграммы (Mermaid) — [diagrams/data_model.md](diagrams/data_model.md), собраны из кода; объяснение — [06_architecture.md](06_architecture.md) §4; схема — `backend/migrations/001_init.sql` |
| Тестовые сценарии | [test-scenarios.md](test-scenarios.md) — сводка из кода; роли и сценарии с перелогином — [15_roles.md](15_roles.md); [02_product.md](02_product.md) §8, [07_resilience.md](07_resilience.md) §6, [13_credit_mechanics.md](13_credit_mechanics.md) §8; автотесты — `backend/tests`, сквозные прогоны всех переходов на живом стенде — `backend/tests/e2e` |
| Коллекция запросов | [api/postman_collection.json](api/postman_collection.json) — Postman v2.1, собрана из кода (`uv run python -m qa.postman`): вход по ID, кабинет и рабочее место специалиста, своя компания с флагами, заявка до выдачи и 9 сценариев со сменой ролей; CI прогоняет её `newman` по стенду в Docker |
| Запуск одной командой | [README](../README.md) в корне: `cd infra && docker compose up --build` |

Пути вида `refs/…` в документах — локальные копии первоисточников у команды, в репозиторий не входят: у каждого источника есть ссылка.
