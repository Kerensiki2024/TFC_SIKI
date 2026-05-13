# n8n — guide de création des workflows

Le backend peut fonctionner sans n8n. Quand tu veux brancher l'orchestration, crée 3 workflows :

## 1. Ingestion_Horaires
**Trigger**: Cron toutes les 15 minutes

Étapes :
1. HTTP Request / fichier source officielle
2. Code node pour normaliser les données
3. Comparaison avec la base locale
4. Appel API backend ou SQL direct pour mettre à jour
5. Si changement détecté → webhook notification

## 2. Edition_Horaire
**Trigger**: Webhook

Le backend envoie un payload structuré, par exemple :
```json
{
  "intent": "MOVE_EVENT",
  "event_id": 4,
  "requested_by": 2,
  "role": "STAFF",
  "new_start_time": "2026-04-20T10:00:00",
  "new_end_time": "2026-04-20T12:00:00",
  "reason": "Prof indisponible"
}
```

Étapes :
1. Webhook
2. Switch sur `intent`
3. Validation métier
4. Si sensible → attente approbation
5. Notification
6. Journalisation

## 3. Notifications
**Trigger**: Webhook

Étapes :
1. Réception message
2. Récupération des destinataires
3. Envoi email/SMS/app
4. Log de livraison
