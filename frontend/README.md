# Фронтенд Fino

Кабинет клиента и рабочее место банка: Vue 3, TypeScript, PrimeVue, Tailwind CSS, тексты на русском и английском (vue-i18n).
Нужен Node.js 20.11.1 (`.nvmrc`) и pnpm 10. Правила разработки — в [`CONTRIBUTING.md`](CONTRIBUTING.md).

```sh
nvm install
nvm use
pnpm install
cp .env.example .env
pnpm dev        # http://localhost:5173; сборка — pnpm build, её просмотр — pnpm preview (4173)
```

Весь стенд с этим фронтом за nginx — `cd ../infra && docker compose up --build`, кабинет на http://localhost:8080.

## Экраны

- `/` — главная продукта, `/login` — выбор пользователя, `/login/company` — конструктор своей компании.
- Кабинет клиента по ИНН `/cabinet/:inn`: главная, кредиты, заявки (новая и карточка заявки), голосование участника по крупной сделке (`votes`).
- Рабочее место банка там же: очередь и досье (`bank/queue`), все заявки (`bank/applications`), метрики (`bank/metrics`).

## Подключение к API

Фронт работает с бэкендом из `backend/` (`cd backend && docker compose up --build`, документация API — `/api/docs` на порту 8000).

- `VITE_API_BASE_URL=/api` — запросы идут через прокси Vite на `API_PROXY_TARGET` (по умолчанию `http://localhost:8000`),
  так же, как за nginx стенда `infra/`. Можно указать и прямой адрес `http://localhost:8000/api` — CORS открыт для 5173 и 4173.
- `FEATURE_K1`, `FEATURE_K2` — прогноз остатка и кредитное предложение на главной; включены, пока не заданы как `false`.
  Выключенную на бэкенде функцию (`FEATURE_OFF`) фронт тоже не показывает.
- Вход: карточка человека на экране входа `/login` вызывает `POST v1/sandbox/personas/{id}/login`, токен хранится в `localStorage`
  и уходит в `Authorization: Bearer`. Выход — `POST v1/auth/logout`. Кабинет открывается по ИНН: `/cabinet/:inn`.
- Пока банк собирает данные компании, API отвечает `409 COMPANY_NOT_LOADED` — клиент сам повторяет запрос.
- Ошибки — RFC 9457; ветвление по `code` (`src/app/types/api-error-code-enum.ts`).

Проверки: `pnpm lint` и `pnpm build` (с проверкой типов `vue-tsc`; образ стенда собирается без неё).
