# Polytech Schedule Chatbot — FastAPI + MySQL + n8n MVP

Ce projet est une base **complète et cohérente** pour ton TFC sur le chatbot de gestion des horaires :
- consultation des horaires par étudiant ;
- édition guidée par personnel administratif ;
- audit et traçabilité ;
- notifications ;
- intégration possible avec **n8n** ;
- base **MySQL** au lieu de PostgreSQL.

## 1. Stack technique
- **FastAPI** pour le backend
- **MySQL 8** pour la base de données
- **SQLAlchemy 2 + Alembic** pour les modèles et migrations
- **JWT local** pour un MVP de sécurité (à remplacer plus tard par SSO/ENT)
- **n8n** branchable via webhooks
- **Docker Compose** pour lancer rapidement l'environnement

## 2. Fonctionnalités incluses
### Étudiant
- connexion JWT
- prochain cours
- planning du jour
- planning de la semaine
- notifications

### Admin / staff
- création d'événement
- annulation d'un cours
- déplacement d'un cours
- gestion des changements sensibles via `proposed_changes`
- audit des modifications

## 3. Démarrage rapide
```bash
cp .env.example .env
docker compose up --build
```

Puis ouvre :
- API docs: `http://localhost:8000/docs`
- n8n: `http://localhost:5678`

## 4. Comptes de démonstration
Le script de seed crée ces comptes avec le mot de passe :

```text
password123
```

- `alice@student.local` → STUDENT
- `bob.staff@polytech.local` → STAFF
- `director@polytech.local` → DIRECTOR

## 5. Variables importantes
Dans `.env` :
- `DATABASE_URL`
- `SECRET_KEY`
- `N8N_EDITION_WEBHOOK_URL`
- `N8N_NOTIFICATION_WEBHOOK_URL`
- `N8N_INGESTION_WEBHOOK_URL`

Si les URLs n8n ne sont pas renseignées, le backend fonctionne quand même localement.

## 6. Arborescence
```text
backend/     -> API FastAPI
n8n/         -> contrats et guides des workflows
shared/      -> exemples de payloads
```

## 7. Remarques
- Le projet est prêt pour un **MVP de soutenance / TFC**.
- Le SSO/ENT réel n'est pas branché : ici il est simulé par JWT.
- Les fichiers n8n fournis sont des **templates et contrats**, pas des exports garantis 1:1 importables.
- La logique respecte le découpage de ton analyse : consultation, édition, validation, audit, notification.
