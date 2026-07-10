# AGENTS.md

## Cursor Cloud specific instructions

### Nature du dépôt
Ce dépôt est **uniquement de la conception** (documentation + schéma SQL). Il n'y a pas de
code applicatif, pas de `package.json`/`requirements.txt`, donc **rien à installer, linter,
tester ou builder**. Le seul artefact exécutable est `db.sql` (DDL PostgreSQL). La stack
décrite dans `ARCHITECTURE.md` (React/Node/Redis/Judge0) est une cible non implémentée.

### Base de données PostgreSQL
- PostgreSQL 16 est installé dans l'image (schéma requiert PostgreSQL 15+). Il fournit les
  extensions `pgcrypto` et `citext` requises par `db.sql`.
- Le cluster n'est pas toujours démarré automatiquement au boot. Pour le démarrer :
  `sudo pg_ctlcluster 16 main start` (vérifier avec `pg_isready`).
- Un rôle de connexion `ubuntu` (SUPERUSER) existe, donc `psql`/`createdb` fonctionnent sans
  `sudo -u postgres`. La base applicative est `cylentic`.
- (Ré)appliquer le schéma (idempotent) : `psql -d cylentic -f db.sql`. Les `NOTICE ... does
  not exist, skipping` sur les triggers sont normaux (idempotence), ce ne sont pas des erreurs.
- Si la base n'existe pas encore : `createdb cylentic` puis `psql -d cylentic -f db.sql`.

### Règle métier à connaître
Le rôle d'un utilisateur est **déduit du préfixe de l'identifiant** et imposé par la contrainte
`chk_role_identifier` sur `cylentic.users` : `ADM-*` → `admin`, `PROF-*` → `teacher`,
`ETU-*` → `student`. Toute insertion incohérente est rejetée par la base.
