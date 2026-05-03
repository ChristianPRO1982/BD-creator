#!/bin/sh

set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="${ENV_FILE:-.env.dev}"
FALLBACK_ENV_FILE=".env.dev.example"
ALEMBIC_INI="api/alembic.ini"

if [ ! -f "$ALEMBIC_INI" ]; then
  echo "Erreur: fichier Alembic introuvable: $ALEMBIC_INI" >&2
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  if [ "$ENV_FILE" = ".env.dev" ] && [ -f "$FALLBACK_ENV_FILE" ]; then
    echo "Info: $ENV_FILE introuvable, utilisation de $FALLBACK_ENV_FILE." >&2
    ENV_FILE="$FALLBACK_ENV_FILE"
  else
    echo "Erreur: fichier d'environnement introuvable: $ENV_FILE" >&2
    echo "Astuce: copier .env.dev.example vers .env.dev, ou définir ENV_FILE=.env.prod." >&2
    exit 1
  fi
fi

case "$ENV_FILE" in
  /*) ENV_PATH="$ENV_FILE" ;;
  *) ENV_PATH="$ROOT_DIR/$ENV_FILE" ;;
esac

if ! command -v uv >/dev/null 2>&1; then
  echo "Erreur: 'uv' n'est pas installé ou non disponible dans PATH." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
. "$ENV_PATH"
set +a

if [ "$#" -eq 0 ]; then
  set -- upgrade head
fi

# When launched from host shell, Docker service hostnames like "postgres"
# are often not resolvable. In that case, fallback to localhost if possible.
if [ "${DB_HOST:-}" = "postgres" ]; then
  if command -v getent >/dev/null 2>&1 && ! getent hosts postgres >/dev/null 2>&1; then
    echo "Info: hôte DB 'postgres' non résolu depuis ce shell, fallback vers 127.0.0.1." >&2
    export DB_HOST="127.0.0.1"
  fi
fi

if [ -n "${PYTHONPATH:-}" ]; then
  export PYTHONPATH="$ROOT_DIR/api:$PYTHONPATH"
else
  export PYTHONPATH="$ROOT_DIR/api"
fi

# Avoid uv warning when another project's virtualenv is currently active.
unset VIRTUAL_ENV || true

echo "Migration Alembic: $*"
echo "Env: $ENV_PATH"
echo "DB: ${DB_HOST:-?}:${DB_PORT:-?}/${DB_NAME:-?} (user=${DB_USER:-?})"

echo "Commande: alembic $*"

exec uv run alembic -c "$ALEMBIC_INI" "$@"
