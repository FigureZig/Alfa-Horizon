# Правила для ИИ-агентов

- Логика и решения — `docs/` (начинать с `docs/README.md`), API — `docs/api/openapi.json`. Разошёлся с ними — сначала issue, потом код.
- Бэкенд — дополнительные правила в `backend/AGENTS.md`.
- Один агент — одна ветка от `main`; маленькие PR; без force-push, без массового реформата.
- `.env` и секреты не коммитим (шаблон — `backend/.env.example`).
- Перед PR: `cd backend && uv run ruff check . && uv run pytest`, `docker compose up --build` поднимается.
