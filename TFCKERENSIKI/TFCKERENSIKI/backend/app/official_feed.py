"""
Source « officielle » simulée — même générateur que le seed (L3GIN).

Utilité : n8n appelle GET /n8n/official-feed pour récupérer un JSON stable,
puis POST /n8n/ingest pour pousser les changements en base (workflow ingestion).
"""
from __future__ import annotations

from datetime import datetime

from app.l3gin_schedule import EVENT_SOURCE, iter_l3gin_week_events
from app.schedules import now_local


def build_official_feed() -> list[dict]:
    """
    Construit la liste des événements de la semaine courante au format JSON-friendly
    (dates en ISO 8601 string pour transport HTTP).
    """
    today_local = now_local().date()

    def iso(dt: datetime) -> str:
        return dt.isoformat()

    out: list[dict] = []
    for row in iter_l3gin_week_events(today_local):
        out.append(
            {
                "matiere": row["matiere"],
                "groupe": row["groupe"],
                "date_debut": iso(row["date_debut"]),
                "date_fin": iso(row["date_fin"]),
                "salle": row["salle"],
                "enseignant": row["enseignant"],
                "type": row["type"],
                "source": EVENT_SOURCE,
            }
        )
    return out
