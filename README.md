# BD Creator V1

## Démarrage dev

1. Copier `.env.dev.example` vers `.env.dev`.
2. Lancer `docker network create pg-carthographie_backend` si besoin.
3. Lancer `docker compose -f compose.yaml -f compose.dev.yaml up --build`.
4. API: `http://localhost:8000` / Web: `http://localhost:5173`.

## Migrations

Exemple:

```bash
uv sync --dev
uv run alembic -c api/alembic.ini upgrade head
```
