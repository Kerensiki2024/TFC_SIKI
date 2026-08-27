# Chatbot intelligent — gestion des horaires (projet Bachelor)

Projet de démonstration aligné sur ta feuille de route : **FastAPI**, **PostgreSQL**, **n8n** (orchestration), interface **React** (Vite).

## Prérequis

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (démarré)
- Node.js **18+** (pour le frontend en local)

## Démarrer le backend et les services

À la racine du dépôt :

```powershell
docker compose up --build
```

- API : http://localhost:8000/docs (Swagger OpenAPI)
- Au **premier démarrage** après cette version, le conteneur `api` exécute **`alembic upgrade head`** (schéma versionné). Si tu avais une ancienne base **sans** Alembic et que les tables existent déjà, l’API répare automatiquement (`create_all` + `stamp`, puis migration **`002_legacy_compat`** pour la colonne `password_hash` et la table `pending_confirmations`). En cas de doute persistant : `docker compose down -v` puis `docker compose up --build`.
- n8n : http://localhost:5678 — crée ton compte au premier accès, puis **importe les workflows** dans le dossier **[`n8n/`](n8n/README.md)** (`ingestion-horaires.api.json`, `webhook-edit-schedule.json`) et suis la procédure décrite dans **`n8n/README.md`**. Les routes API dédiées sont **`/n8n/official-feed`** et **`/n8n/ingest`** (voir Swagger).

## Frontend (chat)

```powershell
cd frontend
npm install
npm run dev
```

Interface : http://localhost:5173 — connexion avec un **e-mail L3GIN** du formulaire (mot de passe `Nom@123`) ou compte agent **bob.agent@univ.demo** / `bob123`. Les mots de passe sont **haches en base** (bcrypt) ; apres mise a jour du modele, un `docker compose down -v` recree la base si besoin.

**Point 3 (frontend)** : validation du JWT au rechargement (`/auth/me`), gestion d’une session expirée sur `/chat` (401), affichage de l’**intent** et du besoin de **confirmation** sous les reponses du bot, labels accessibles sur le formulaire de connexion.

Tu peux forcer l’URL de l’API avec un fichier `.env` dans `frontend` :

```
VITE_API_URL=http://localhost:8000
```

## Tester rapidement les intentions (étudiant L3GIN)

- « Quel est mon prochain cours ? »
- « Mes cours aujourd'hui »
- « Montre-moi ma semaine »
- « Quand est le cours de Travaux de Programmation ? »

## Tester l’annulation (agent / bob)

1. Connecte-toi avec **bob.agent@univ.demo** / `bob123`
2. Par exemple : « Annule le cours de Travaux de Programmation groupe L3GIN »
3. Réponds « oui » pour confirmer (obligatoire avant suppression en base)

## Autres actions agent (même principe : proposition puis « oui » / « non »)

- **Déplacer** : « Déplace le cours de Travaux de Programmation demain » (ou « dans 3 jours », « semaine prochaine »…)
- **Changer de salle** : « Mets le cours de Programmation Orientée Objet en salle H »
- **Créer** : « Crée un cours de Séminaire salle B » (créneau démo : lendemain 08:30–10:30, fuseau Europe/Paris)
- **Historique** : « Y a-t-il des changements ? » / « notification » → dernières lignes du journal d’audit

## Structure

- `backend/app` — modèles (`events`, `users`, `change_requests`, `audit_logs`, `pending_confirmations`), NLU, routes `/chat`, `/health`
- `backend/alembic` — migrations PostgreSQL (`001_initial`)
- `backend/tests` — tests pytest (SQLite en mémoire, sans Docker DB)
- `frontend` — SPA de chat minimale pour la démo
- `docker-compose.yml` — PostgreSQL + n8n + API

## Migrations (développement local hors Docker)

Dans `backend/` avec `DATABASE_URL` pointant vers ta base :

```powershell
cd backend
py -3 -m alembic upgrade head
```

(Alembic utilise **psycopg** en synchrone ; l’API reste en **asyncpg**.)

## Tests automatisés (recommandé : image Docker Python 3.12)

```powershell
docker compose build api
docker run --rm -w /app tfckerensiki-api pytest tests/ -q
```

## Suite possible (mémoire)

- Workflow n8n **ingestion** (timer 15 min) vers une vraie source d’horaires
- Affiner le NLU (dates/heures libres pour déplacement et création)
- Rate limiting sur `/auth/login`, déploiement cloud
