# Rapport d'avancement - Projet Bachelor

## 1) Informations du projet

- **Sujet** : Developpement et deploiement d'un chatbot intelligent pour la gestion des horaires de cours
- **Etudiante** : Keren Siki
- **Periode couverte** : Mai 2026 (demarrage technique)
- **Version du rapport** : v0.1 (brouillon evolutif)

## 2) Rappel du contexte

Le projet vise a centraliser la gestion et la consultation des horaires via un chatbot.  
L'objectif est de permettre :

- aux etudiants de consulter les horaires en langage naturel ;
- au personnel habilite de modifier les horaires de facon tracee ;
- a l'institution de garantir notification, audit et gouvernance des changements.

## 3) Objectifs techniques du MVP

- Mettre en place une architecture operationnelle (API + DB + n8n).
- Construire des workflows n8n alignes sur le guide methodologique.
- Obtenir un premier cycle de tests executables pour la soutenance.

## 4) Travail realise (etat actuel)

### 4.1 Infrastructure

- Environnement Docker compose initialise.
- Services operationnels : `api`, `db`, `n8n`.
- Resolution des conflits de ports (5432, 8000) durant le demarrage.

### 4.2 Backend/API

- Base FastAPI en place.
- Endpoints d'integration n8n disponibles pour ingestion :
  - `GET /n8n/official-feed`
  - `POST /n8n/ingest`
- Endpoint principal de dialogue :
  - `POST /chat`

### 4.3 Workflows n8n prepares/importes

Workflows alignes sur le guide (5 blocs) :

1. `n8n/workflows/ingestion-horaires.pro-guide.json`
2. `n8n/workflows/consultation-horaires.webhook.json`
3. `n8n/workflows/edition-horaires.webhook.json`
4. `n8n/workflows/notifications-changements.execute.json`
5. `n8n/workflows/audit-logs.webhook.json`

### 4.4 Validation fonctionnelle observee

- Ingestion executee avec succes dans n8n.
- Appel du sous-workflow de notifications configure (node execute sub-workflow).
- Import des workflows confirme dans l'interface n8n.

### 4.5 Frontend (etat de progression)

- Interface chat React/Vite operationnelle et connectee a l'API `/chat`.
- Profils de test integres (etudiant/agent) pour simuler les roles.
- Ajout d'un indicateur de disponibilite backend (`/health`).
- Ajout de suggestions rapides pour accelerer les tests de demonstration.
- Ajout d'un bouton de reinitialisation de conversation.
- Historique du chat stocke localement (localStorage) pour conserver la session.
- Ajout d'un ecran de connexion (email/mot de passe) avec token JWT.
- La session utilisateur est maintenue via `sessionStorage` (token + profil).

### 4.6 Authentification (phase A locale)

- Endpoint `POST /auth/login` implemente (comptes de demo).
- Endpoint `GET /auth/me` implemente pour recuperer l'identite connectee.
- Route `POST /chat` protegee par Bearer token (JWT).
- Suppression de `user_email` dans le payload chat : l'identite vient du token.
- Test de fumee valide : login + appel `/chat` authentifie fonctionnels.

### 4.7 Promotion unique L3GIN (donnees reelles formulaire)

- Horaires : une seule promotion **L3GIN**, alignee sur l'emploi du temps Faculté Polytechnique (UNIKIN).
- Salles : repartition **A a H** (rotation sur les creneaux).
- Etudiants : comptes crees a partir du formulaire **L3GIN2025** ; mot de passe = **`<Nom>@123`** (Nom = colonne Nom du formulaire).
- Exemple : `kerensiki@gmail.com` / `Makula@123`.
- Agent demo : `bob.agent@univ.demo` / `bob123`.

### 4.8 Backend — point 2 (securisation authentification)

- Mots de passe stockes sous forme **hachee (bcrypt)** dans `users.password_hash` (plus de comparaison en clair au login).
- Module `app/passwords.py` : `hash_password` / `verify_password`.
- Le seed recalcule les hash a chaque demarrage pour les comptes L3GIN + agent.
- Module `app/deps.py` : dependances `require_roles` / `require_agent` pour les routes futures (droits).
- Variable d'environnement `JWT_SECRET` supportee (definie dans `docker-compose` pour la demo).

### 4.9 Frontend — point 3 (experience session et transparence NLU)

- **Bootstrap session** : au chargement de la page, si un JWT est present dans `sessionStorage`, appel `GET /auth/me` pour valider le token et rafraichir le profil (sans boucle de requetes : effet uniquement au montage).
- **401 sur `/chat`** : deconnexion automatique et message invitant a se reconnecter (token expire ou invalide).
- **Reponses enrichies** : affichage sous chaque bulle bot de l'**intent** renvoye par l'API et d'un badge **confirmation** lorsque `needs_confirmation` est vrai (utile en demonstration / trace NLU).
- **Accessibilite legere** : labels associes aux champs login et au textarea (`sr-only`), attributs `autoComplete` sur les champs d'authentification.

### 4.10 Backend — modifications agent (deplacer, salle, creer) + audit « notifications »

- Meme flux que l'annulation : proposition puis confirmation **oui** / **non** (voir 4.11 : desormais en base).
- **deplacer** : decalage en jours (demain, dans N jours, semaine prochaine) avec conservation des heures ; audit `deplacer_cours` ; webhook n8n `intent=deplacer`.
- **changer_salle** : extraction **salle A–H** et matiere ; audit `changer_salle` ; webhook `intent=changer_salle`.
- **creer** : creneau fixe demo **lendemain 08:30–10:30** (Europe/Paris), `source=agent-chat` ; audit `creer_cours`.
- **notif_changement** : affichage des **8 derniers** enregistrements `audit_logs` (demo « changements institutionnels »).
- NLU : intentions modification placees **avant** `recherche_matiere` pour eviter les faux positifs sur le mot « cours » ; matching matiere **sans accents** cote filtre.

### 4.11 Persistance, migrations et tests (finalisation technique)

- **Confirmations** : table `pending_confirmations` (email utilisateur + payload JSON) ; plus de dict processus — les propositions « oui/non » survivent au redemarrage de l'API.
- **Alembic** : revision `001_initial` (tout le schema) ; `init_db()` au demarrage lance `alembic upgrade head` (psycopg synchrone pour la CLI, asyncpg pour l'API).
- **Tests** : `backend/tests/` avec pytest + httpx, SQLite `StaticPool` + seed ; couvre `/health`, login, `/chat` avec et sans JWT, flux agent annulation + `non`.

## 5) Difficultes rencontrees et corrections

### Probleme 1 : Docker indisponible
- **Symptome** : `failed to connect to docker API ... dockerDesktopLinuxEngine`
- **Cause** : Docker Desktop non demarre
- **Correction** : demarrage de Docker Desktop + relance compose

### Probleme 2 : Conflit port PostgreSQL
- **Symptome** : `bind for 0.0.0.0:5432 failed: port is already allocated`
- **Cause** : autre conteneur PostgreSQL actif
- **Correction** : arret/suppression des conteneurs concurrents et relance propre

### Probleme 3 : Conflit port API
- **Symptome** : `bind for 0.0.0.0:8000 failed`
- **Cause** : ancien backend occupant le port
- **Correction** : nettoyage des orphelins puis redemarrage de la stack

### Probleme 4 : Node execute workflow obsolete
- **Symptome** : node "out of date", `workflow id` vide
- **Correction** : remplacement par `Execute A Sub Workflow` et reselection du workflow cible

## 6) Preuves de progression a conserver

- Captures :
  - ecran workflows importes ;
  - execution succes ingestion ;
  - statut services docker ;
  - appels webhook (consultation/edition/audit).
- Exports JSON des workflows dans `n8n/workflows/`.
- Reponses API de test (Swagger / curl / Postman).

## 7) Taches restantes (court terme)

- Verifier et documenter l'activation de chaque workflow.
- Tester officiellement les 3 webhooks :
  - `/webhook/consultation`
  - `/webhook/edition-horaire`
  - `/webhook/audit-log`
- Ajouter resultats de test (payload + sortie) dans ce rapport.
- Ajouter 2 a 3 captures frontend (etat connected/offline + scenario etudiant/agent).

## 8) Journal d'avancement (a completer a chaque session)

### Session 01 - Mise en route technique
- Mise en place projet, docker compose, backend, workflows.
- Deblocage docker + ports.
- Import n8n et premier run ingestion.

### Session 02 - (a renseigner)
- Date :
- Objectifs :
- Actions realisees :
- Resultats :
- Blocages :
- Decisions :

---

## 9) Format recommande pour les prochaines mises a jour

Pour chaque nouvelle etape, ajouter :

1. **Contexte**
2. **Action realisee**
3. **Resultat obtenu**
4. **Preuve (capture / log / fichier)**
5. **Prochaine action**

Ce document est volontairement evolutif et servira de base au chapitre de realisation/validation du memoire.
