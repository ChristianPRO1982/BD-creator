# BD Creator V1

## Démarrage dev

1. Copier `.env.dev.example` vers `.env.dev`.
2. Lancer `docker network create pg-carthographie_backend` si besoin.
3. Vérifier que la base PostgreSQL commune est accessible sur le réseau partagé et que les identifiants `DB_*` de `.env.dev` sont valides.
4. Lancer `docker compose -f compose.yaml -f compose.dev.yaml up --build`.
5. API: `http://localhost:8000` / Web: `http://localhost:5173`.

## Migrations

Commande recommandée:

```bash
./scripts/migrate.sh
```

Les migrations gèrent uniquement le schéma applicatif `bd` dans la base partagée (création/évolution de schéma et tables), jamais la création de la base PostgreSQL elle-même.

Commandes utiles:

```bash
./scripts/migrate.sh current
./scripts/migrate.sh history
./scripts/migrate.sh downgrade -1
```

La documentation complète du script est disponible ici: [scripts/migrate.md](/home/utilisateur/Documents/projects/perso/cARThographie/BD-creator/scripts/migrate.md)
