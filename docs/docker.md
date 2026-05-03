# Docker FastAPI: pattern aligne sur projet-lyrics

## Objectif

Ce projet suit le meme pattern Docker que `docs/projet-lyrics`:

- `Dockerfile` unique,
- `compose.yaml` base,
- `compose.dev.yaml` override dev,
- `compose.prod.yaml` override prod,
- `.env.dev` et `.env.prod` separes,
- reseau backend partage pour la base PostgreSQL commune.

Important: ce projet **ne cree pas** de service PostgreSQL local dans Compose.
Il consomme la base commune et ne gere que son schema SQL (`bd`) via migrations Alembic.

## Architecture retenue

- `compose.yaml`: declaration du reseau partage `shared_backend`.
- `compose.dev.yaml`: services `api`, `web`, `minio`, `auth_mock`.
- `compose.prod.yaml`: services `api` et `web` derriere Traefik.

## Regle BDD

- Base: PostgreSQL commune (ex: `carthographie`).
- Schema applicatif: `bd`.
- Evolutions BDD: uniquement via migrations SQL Alembic.
- Jamais de creation manuelle des tables.

## Environnement DB

Exemple `.env.dev`:

```dotenv
DB_HOST=postgres
DB_PORT=5432
DB_NAME=carthographie
DB_USER=app_bd
DB_PASSWORD=change-me
```

Note:

- En execution depuis un conteneur du reseau Docker partage, `DB_HOST=postgres` est attendu.
- En execution depuis le shell host (hors DNS Docker), le script `scripts/migrate.sh` applique automatiquement un fallback vers `127.0.0.1` si `postgres` n'est pas resolvable.

## Commandes dev

```bash
cp .env.dev.example .env.dev
docker network create pg-carthographie_backend || true
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

## Commandes prod

```bash
cp .env.prod.example .env.prod
docker compose --env-file .env.prod -f compose.yaml -f compose.prod.yaml pull
docker compose --env-file .env.prod -f compose.yaml -f compose.prod.yaml up -d
```

## Migrations

Commande recommandee:

```bash
./scripts/migrate.sh
```

Exemples:

```bash
./scripts/migrate.sh current
./scripts/migrate.sh history
./scripts/migrate.sh downgrade -1
ENV_FILE=.env.prod ./scripts/migrate.sh upgrade head
```

## Checks rapides

- `GET /health` repond `{"status": "ok"}`.
- `api` rejoint bien `shared_backend`.
- Le schema `bd` existe et la revision Alembic courante est `head`.

## Rappels

- Ce projet gere le schema `bd`, pas l'instance PostgreSQL.
- La table utilisateur de reference reste `users.users` (lecture seule) pour l'autorisation SSO.
