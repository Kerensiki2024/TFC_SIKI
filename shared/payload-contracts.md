# Contrats JSON backend -> n8n

## Annulation
```json
{
  "intent": "CANCEL_EVENT",
  "event_id": 12,
  "requested_by": 2,
  "role": "STAFF",
  "reason": "Prof malade",
  "timestamp": "2026-04-19T14:00:00Z"
}
```

## Déplacement sensible
```json
{
  "intent": "MOVE_EVENT",
  "sensitive": true,
  "event_id": 7,
  "requested_by": 2,
  "role": "STAFF",
  "old_start_time": "2026-04-20T08:00:00",
  "old_end_time": "2026-04-20T10:00:00",
  "new_start_time": "2026-04-28T10:00:00",
  "new_end_time": "2026-04-28T12:00:00",
  "new_room_id": 3,
  "reason": "Examen déplacé"
}
```
