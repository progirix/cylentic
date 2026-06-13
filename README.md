# Cylentic

Cylentic est une plateforme web d'examens de programmation securises pour
etablissements d'enseignement. Le MVP cible permet aux professeurs de creer des
examens Python, aux etudiants de composer dans un IDE navigateur verrouille, et
a la plateforme de corriger automatiquement les soumissions via Judge0.

## Livrables inclus

- [`ARCHITECTURE.md`](./ARCHITECTURE.md) : architecture globale, diagramme de
  plateforme, flux MVP et arborescence projet cible.
- [`db.md`](./db.md) : documentation du schema relationnel, tables, attributs,
  relations et cardinalites.
- [`db.sql`](./db.sql) : script PostgreSQL complet, de la creation de la base
  aux tables, contraintes, index, triggers et donnees initiales.

## Stack cible MVP

- Frontend : React, TypeScript, Monaco Editor.
- Backend : Node.js, Express, TypeScript.
- Base de donnees : PostgreSQL.
- Sessions, timers et jobs : Redis.
- Execution de code : Judge0 auto-heberge dans Docker.
- Deploiement : VPS avec Docker Compose et reverse proxy TLS.

## Demarrage base de donnees

Depuis une instance PostgreSQL accessible avec un role autorise a creer une
base :

```bash
psql -f db.sql
```

Le script cree la base `cylentic`, active les extensions necessaires et insere
les plans commerciaux initiaux.
