# Cylentic

**Plateforme d'examens de programmation en navigateur sécurisé.**

Cylentic permet à un étudiant de coder un examen directement dans le navigateur — sans pouvoir en sortir ni utiliser d'aide extérieure — avec un IDE intégré, une exécution de code en sandbox isolé et une correction automatique par tests unitaires.

Ce dépôt contient la **conception du MVP** : l'architecture du système, le modèle de données et le schéma SQL complet. Le MVP est volontairement resserré (Python, anti-triche core, correction automatique) mais conçu pour être extensible (multi-langages, QCM avancé, facturation, API publique).

## Acteurs

| Acteur | Rôle | Identifiant |
|--------|------|-------------|
| Admin établissement | Gère l'école, les comptes, les classes et le plan | `ADM-…` |
| Professeur | Crée/publie les examens, corrige, voit les résultats | `PROF-…` |
| Étudiant | Compose les examens (code + mot de passe + code d'examen) | `ETU-…` |

> Le rôle est **déduit automatiquement** du format de l'identifiant — jamais choisi manuellement.

## Livrables de conception

| Fichier | Contenu |
|---------|---------|
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | Architecture globale, diagrammes (général, ERD, flux), stack technique, arborescence du projet, déploiement, axes d'extensibilité |
| [`db.md`](./db.md) | Modèle de données détaillé : tables, attributs, relations, cardinalités, index, invariants métier |
| [`db.sql`](./db.sql) | DDL PostgreSQL complet et exécutable : création de la base, types, tables, contraintes, index, triggers et données de référence |

## Stack technique (cible)

React + Monaco Editor · Node.js/Express · PostgreSQL · Redis · Judge0 (Docker) · JWT · Docker Compose.

Voir [`ARCHITECTURE.md`](./ARCHITECTURE.md) pour le détail.

## Initialiser la base de données

```bash
# 1. Créer la base (en tant que superutilisateur PostgreSQL)
createdb cylentic

# 2. Appliquer le schéma complet
psql -d cylentic -f db.sql
```

Le script crée le schéma `cylentic`, l'ensemble des tables, index et triggers, puis insère les 4 plans tarifaires (Gratuit, Starter, Pro, Enterprise).
