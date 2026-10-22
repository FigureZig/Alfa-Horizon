# Сторонние компоненты и лицензии

Что входит в стенд и под какими лицензиями. Версии — из `backend/uv.lock`, `frontend/pnpm-lock.yaml` и образов `infra/docker-compose.yml`;
лицензии — из метаданных пакетов (Python — `importlib.metadata` в образе API, npm — реестр npmjs.org для версии из lock-файла).
Проверено 22.10.2026. Платных и закрытых сервисов нет; ML-моделей и LLM в стенде нет.

## Образы Docker

| Образ | Версия | Лицензия | Где |
|---|---|---|---|
| PostgreSQL (`postgres:17-alpine`) | 17.11 | PostgreSQL License | база |
| WireMock (`wiremock/wiremock:3.9.1`) | 3.9.1 | Apache-2.0 | моки внешних систем |
| Python (`python:3.13-slim`) | 3.13.16 | PSF-2.0 | API и worker |
| uv | 0.11.26 | MIT OR Apache-2.0 | установка зависимостей в образе |
| Node.js (`node:20.11.1-alpine`) | 20.11.1 | MIT | только сборка фронта |
| nginx (`nginx:1.27-alpine`) | 1.27.5 | BSD-2-Clause | раздача фронта и прокси `/api` |

Базовые образы содержат пакеты дистрибутивов Alpine и Debian под их собственными лицензиями.

## Бэкенд: что попадает в образ

| Пакет | Версия | Лицензия |
|---|---|---|
| fastapi | 0.157.0 | MIT |
| starlette | 1.9.0 | BSD-3-Clause |
| pydantic / pydantic_core | 2.14.1 / 2.50.1 | MIT |
| uvicorn[standard] | 0.54.0 | BSD-3-Clause |
| uvloop | 0.23.0 | Apache-2.0 и MIT |
| httptools | 0.9.0 | MIT |
| watchfiles | 1.3.0 | MIT |
| websockets | 17.3 | BSD-3-Clause |
| python-dotenv | 1.2.4 | BSD-3-Clause |
| asyncpg | 0.32.0 | Apache-2.0 |
| httpx / httpcore | 0.28.1 / 1.0.9 | BSD-3-Clause |
| h11 | 0.16.0 | MIT |
| anyio | 4.15.1 | MIT |
| idna | 3.20 | BSD-3-Clause |
| certifi | 2026.10.19 | MPL-2.0 |
| click | 8.5.0 | BSD-3-Clause |
| PyYAML | 6.0.3 | MIT |
| typing_extensions | 4.16.0 | PSF-2.0 |
| annotated-types, annotated-doc, typing-inspection | 0.8.0, 0.0.5, 0.4.4 | MIT |
| opentelemetry-api | 1.45.1 | Apache-2.0 |

Только для разработки и тестов (в образ не входят): pytest 9.1.1 (MIT), ruff 0.17.1 (MIT), networkx 3.7 (BSD-3-Clause) — граф статусов,
allpairspy 2.5.1 (MIT) — pairwise-наборы, pluggy 1.7.0 и iniconfig 2.3.1 (MIT), packaging 26.3 (Apache-2.0 OR BSD-2-Clause),
Pygments 2.21.0 (BSD-2-Clause).

## Фронт

| Пакет | Версия | Лицензия |
|---|---|---|
| vue | 3.5.44 | MIT |
| vue-router | 5.4.0 | MIT |
| pinia | 3.0.4 | MIT |
| vue-i18n | 11.4.16 | MIT |
| primevue, @primeuix/themes, primeicons | 4.4.1, 1.2.5, 7.0.0 | MIT |
| axios | 1.20.0 | MIT |
| lodash-es | 4.18.1 | MIT |

Для сборки: vite 6.4.1, @vitejs/plugin-vue 5.2.4, tailwindcss и @tailwindcss/vite 4.3.3, tailwindcss-primeui 0.6.1, vue-tsc 3.3.13,
eslint 9.39.1, eslint-plugin-vue 10.11.1, @vue/eslint-config-typescript 14.9.0, @types/lodash-es 4.17.12 — MIT; typescript 5.9.3 — Apache-2.0.
Транзитивные зависимости — в `frontend/pnpm-lock.yaml`.

## Что смоделировано, а не подключено

Реальных банковских и государственных систем в стенде нет: эксперты кейса просили автономный воспроизводимый прототип на моках
и синтетике. Каждая система ниже — стабы WireMock в форматах первоисточника (`docs/09_data_contracts.md`), ответы строит
`backend/seed/world.py` из вымышленного мира `backend/seed/personas.yaml`.

| Система | Формат, на который опираемся |
|---|---|
| ЕГРЮЛ, ЕГРИП | XSD ФНС, версия формата 4.06 |
| Открытые данные ФНС: реестр МСП, численность, уплаченные налоги, недоимки, налоговые режимы, дисквалифицированные лица | XSD и паспорта наборов nalog.gov.ru |
| ГИР БО (бухгалтерская отчётность) | структура ответа bo.nalog.gov.ru |
| Бюро кредитных историй | формат кредитного отчёта ЦБ v3.4, информационная часть |
| Реестр МЧД | статусы публичного сервиса m4d.nalog.gov.ru; коды полномочий — плейсхолдер |
| ЕИС (госконтракты) | сокращённый контракт: номер, заказчик, цена, даты, аванс — упрощение |
| Юридические проверки (банкротство, суды, исполнительные производства) | сокращённый сводный ответ — упрощение |
| Банк: карточка клиента, доступы ДБО, устав, выписка по счёту, АБС (выдача) | внутренние контракты, описаны в `docs/09_data_contracts.md` |

Все компании, люди, ИНН, ОГРН, СНИЛС и счета вымышленные: контрольные цифры правильные, совпадение с реальными лицами случайно.
Нормы права, ставки ЦБ и рыночные цифры — со ссылками на первоисточники в `docs/10_sources.md`.
