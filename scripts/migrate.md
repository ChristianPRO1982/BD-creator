# Aide - `scripts/migrate.sh`

Ce script applique les migrations Alembic sur la base PostgreSQL commune, en s'appuyant sur un fichier d'environnement (`.env.dev` par défaut).

## Prérequis

- Être à la racine du projet `BD-creator` (ou lancer le script via son chemin).
- Avoir `uv` installé et disponible dans le `PATH`.
- Avoir un fichier d'environnement valide (`.env.dev` ou `.env.prod`) avec:
  - `DB_HOST`
  - `DB_PORT`
  - `DB_NAME` (attendu: `carthographie`)
  - `DB_USER`
  - `DB_PASSWORD`

## Commande par défaut

```bash
./scripts/migrate.sh
```

Équivalent à:

```bash
./scripts/migrate.sh upgrade head
```

## Commandes utiles

Le script relaie directement les arguments à Alembic.

Afficher la révision courante:

```bash
./scripts/migrate.sh current
```

Voir l'historique des migrations:

```bash
./scripts/migrate.sh history
```

Revenir d'une migration:

```bash
./scripts/migrate.sh downgrade -1
```

Passer à une révision spécifique:

```bash
./scripts/migrate.sh upgrade 0001_initial
```

## Choisir un autre fichier d'environnement

Par défaut, le script charge `.env.dev`.
Si `.env.dev` est absent, le script bascule automatiquement sur `.env.dev.example` (avec un message `Info`).

Pour utiliser `.env.prod`:

```bash
ENV_FILE=.env.prod ./scripts/migrate.sh upgrade head
```

## Sortie attendue

Le script affiche:

- l'action Alembic (`upgrade`, `downgrade`, `current`, etc.),
- le fichier d'environnement utilisé,
- la cible DB (`host:port/db` + user),

puis exécute:

```bash
uv run alembic -c api/alembic.ini <arguments>
```

Le script ajoute automatiquement `api/` au `PYTHONPATH` pour que les imports Alembic (`app.*`) fonctionnent.
Si `DB_HOST=postgres` n'est pas résolu depuis le shell local, le script bascule automatiquement vers `127.0.0.1`.

## Dépannage rapide

- `fichier d'environnement introuvable`:
  - vérifier `ENV_FILE` ou créer `.env.dev`,
  - exemple: `cp .env.dev.example .env.dev`.
- `'uv' n'est pas installé`:
  - installer `uv` puis relancer.
- erreur de connexion PostgreSQL:
  - vérifier les variables `DB_*`,
  - vérifier l'accès au réseau partagé Docker (`SHARED_DB_NETWORK`),
  - vérifier que la base commune est joignable.
