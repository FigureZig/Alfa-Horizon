# Фронтенд Fino

Кабинет клиента и рабочее место банка: Vue 3, TypeScript, PrimeVue, Tailwind CSS. Нужен Node.js 20.11.1 и pnpm 10.
Правила разработки — в [`CONTRIBUTING.md`](CONTRIBUTING.md).

```sh
nvm install
nvm use
pnpm install
cp .env.example .env
pnpm dev
```

## Подключение к API

Фронт работает с бэкендом из `backend/` (`cd backend && docker compose up --build`, документация API — `/api/docs` на порту 8000).

- `VITE_API_BASE_URL=/api` — запросы идут через прокси Vite на `API_PROXY_TARGET` (по умолчанию `http://localhost:8000`),
  так же, как за nginx стенда `infra/`. Можно указать и прямой адрес `http://localhost:8000/api` — CORS открыт для 5173 и 4173.
- Вход: карточка человека на экране входа `/login` вызывает `POST v1/sandbox/personas/{id}/login`, токен хранится в `localStorage`
  и уходит в `Authorization: Bearer`. Выход — `POST v1/auth/logout`. Кабинет открывается по ИНН: `/cabinet/:inn`.
- Пока банк собирает данные компании, API отвечает `409 COMPANY_NOT_LOADED` — клиент сам повторяет запрос.
- Ошибки — RFC 9457; ветвление по `code` (`src/app/types/api-error-code-enum.ts`).

Проверки: `pnpm lint` и `pnpm build`.

