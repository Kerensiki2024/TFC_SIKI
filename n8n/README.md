# n8n — import et mise en route

Ce dossier correspond au **rôle de n8n dans ton mémoire** : orchestrer l’ingestion périodique et réagir aux évènements envoyés depuis le chatbot (webhook après une annulation confirmée).

## Prérequis

- `docker compose up` à la racine du projet (**Docker Desktop** démarré).
- Interfaces : API http://localhost:8000/docs, n8n http://localhost:5678 .

## Sécurité intégration API

Pour les routes `/n8n/*`, Compose définit :

`N8N_INTERNAL_SECRET=dev-n8n-secret`

L’API attend l’en-tête **`X-N8N-Secret: dev-n8n-secret`** (déjà renseigné dans les fichiers JSON d’workflow).

Sans Docker, si tu lances l’API en local sans variable `N8N_INTERNAL_SECRET`, les routes `/n8n/*` sont accessibles sans en-tête (pratique pour débuguer).

## Workflows du guide (5)

Tu as maintenant une version alignée sur le document **TFCKERENSIKIMAKULA** avec 5 workflows distincts :

1. `workflows/ingestion-horaires.pro-guide.json` (ingestion structurée avec normalisation + IF)
2. `workflows/consultation-horaires.webhook.json` (consultation via webhook)
3. `workflows/edition-horaires.webhook.json` (édition avec validation permissions + sensibilité)
4. `workflows/notifications-changements.execute.json` (notifications déclenchées par Execute Workflow)
5. `workflows/audit-logs.webhook.json` (audit logs enrichis via webhook)

Les anciens fichiers existent toujours et peuvent servir de fallback :
- `workflows/ingestion-horaires.api.json`
- `workflows/webhook-edit-schedule.json`

## 1. Workflow « ingestion » (`workflows/ingestion-horaires.pro-guide.json`)

1. Dans n8n : **Workflows → Import from file** → choisir ce JSON.
2. Vérifie les URLs HTTP :
   - Avec Docker Compose (**recommandé**), garde **`http://api:8000/...`** (nom du service défini dans `docker-compose.yml`).
   - Si n8n tourne **sur ta machine** et l’API dans Docker expose le port **8000**, remplace par **`http://host.docker.internal:8000`** (Windows / macOS Docker Desktop).
3. **Active** le workflow (bouton *Active*) pour les exécutions planifiées.
4. Test manuel : nœud **GET source officielle** → **Test step**, puis chaîne jusqu’à **POST ingest API**. Tu dois voir `created` / `updated` dans la réponse.

Résumé fonctionnel :

- **Scheduler** → **GET `/n8n/official-feed`** (source officielle **simulée** par l’API) → **POST `/n8n/ingest`** (upsert en base PostgreSQL).

## 2. Workflow « consultation » (`workflows/consultation-horaires.webhook.json`)

1. Importer puis activer.
2. Endpoint exposé : `POST /webhook/consultation`
3. Payload exemple :

```json
{
  "groupe": "L1-INFO-A",
  "type_requete": "planning_jour"
}
```

Valeurs supportées pour `type_requete` : `planning_jour`, `planning_semaine`, `prochain_cours`.

## 3. Workflow « édition » (`workflows/edition-horaires.webhook.json`)

1. Importer puis activer.
2. Endpoint exposé : `POST /webhook/edition-horaire`
3. Ce workflow suit le guide : validation des permissions puis classification de sensibilité.

Payload exemple :

```json
{
  "user_id": 123,
  "user_role": "agent",
  "action": "change_room",
  "course_id": 456,
  "new_room": "C12"
}
```

## 4. Workflow « notifications » (`workflows/notifications-changements.execute.json`)

- Déclencheur : **Execute Workflow Trigger** (comme dans le guide).
- À appeler depuis ingestion/édition via un nœud **Execute Workflow**.
- Actuellement il prépare les messages ; tu peux brancher ensuite SMTP/Email node.

## 5. Workflow « audit logs » (`workflows/audit-logs.webhook.json`)

- Endpoint : `POST /webhook/audit-log`
- Le workflow enrichit les logs (timestamp + hash simple) avant réponse.
- Étape suivante recommandée : ajouter un nœud PostgreSQL pour insertion réelle.

## 6. Ancien workflow « webhook édition » (`workflows/webhook-edit-schedule.json`)

1. Importer puis **Activer** le workflow.
2. Le chatbot FastAPI envoie un POST à  
   **`http://n8n:5678/webhook/edit-schedule`** (depuis le conteneur API, déjà défini dans `docker-compose`).
3. Test : depuis la doc Swagger `POST http://localhost:8000/chat` avec un scénario d’annulation (profil **bob**) puis « oui » — l’exécution doit apparaître dans n8n (ou une erreur si le workflow n’est pas actif).

Ensuite tu peux ajouter des nœuds **Gmail / SMTP / Slack** après le Webhook pour les **notifications** décrites dans le cahier des charges.

## Pour le mémoire

- Capture d’écran des **5 workflows** + au moins 1 exécution réussie pour chacun.
- Schéma : *Ingestion* + *Consultation* + *Édition* + *Notifications* + *Audit*.
- Explique comment la source réelle de la faculté remplacerait **`/n8n/official-feed`** (fichier issu du planning, FTP, REST du SI, etc.).
