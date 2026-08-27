"""
Points d’intégration appelés par n8n (ou scripts) : « flux officiel » simulé + ingestion en base.

Sécurité optionnelle : si N8N_INTERNAL_SECRET est défini dans l’API, chaque requête doit envoyer
l’en-tête HTTP X-N8N-Secret avec la même valeur (docker-compose : dev-n8n-secret).
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models import Event
from app.official_feed import build_official_feed

router = APIRouter(prefix="/n8n", tags=["n8n"])


class OfficialEventIn(BaseModel):
    """Un créneau reçu du workflow n8n (JSON), aligné sur le modèle Event."""
    matiere: str
    groupe: str
    date_debut: datetime
    date_fin: datetime
    salle: str
    enseignant: str
    type: str = "cours"
    source: str = "officielle"


class IngestBody(BaseModel):
    events: list[OfficialEventIn] = Field(..., min_length=0)


def _to_utc(dt: datetime) -> datetime:
    """Normalise en UTC pour comparaisons stables en base (naïf = supposé UTC)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _check_secret(x_n8n_secret: str | None) -> None:
    """401 si un secret est configuré côté API mais absent ou incorrect."""
    expected = settings.n8n_internal_secret
    if not expected:
        return
    if x_n8n_secret != expected:
        raise HTTPException(status_code=401, detail="X-N8N-Secret invalide")


@router.get("/official-feed")
async def official_feed(x_n8n_secret: Annotated[str | None, Header()] = None):
    """
    Simule la source officielle (ERP / fichier) que n8n récupère avant ingestion.
    Retourne une liste d’événements pour la semaine courante (générateur L3GIN).
    """
    _check_secret(x_n8n_secret)
    events = build_official_feed()
    return {"events": events, "count": len(events)}


@router.post("/ingest")
async def ingest_official_schedule(
    body: IngestBody,
    session: AsyncSession = Depends(get_session),
    x_n8n_secret: Annotated[str | None, Header()] = None,
):
    """
    Upsert : pour chaque événement entrant, met à jour une ligne existante ou en crée une nouvelle.
    Clé métier démo : (groupe, matiere, date_debut) en UTC — à affiner si collisions réelles.
    """
    _check_secret(x_n8n_secret)
    created = 0
    updated = 0

    async with session.begin():
        for raw in body.events:
            dd = _to_utc(raw.date_debut)
            df = _to_utc(raw.date_fin)

            res = await session.execute(
                select(Event)
                .where(Event.groupe == raw.groupe)
                .where(Event.matiere == raw.matiere)
                .where(Event.date_debut == dd)
            )
            existing = res.scalar_one_or_none()

            if existing:
                dirty = False
                for attr, val in (
                    ("date_fin", df),
                    ("salle", raw.salle),
                    ("enseignant", raw.enseignant),
                    ("type", raw.type),
                    ("source", raw.source),
                ):
                    if getattr(existing, attr) != val:
                        setattr(existing, attr, val)
                        dirty = True
                if dirty:
                    updated += 1
                continue

            session.add(
                Event(
                    matiere=raw.matiere,
                    groupe=raw.groupe,
                    date_debut=dd,
                    date_fin=df,
                    salle=raw.salle,
                    enseignant=raw.enseignant,
                    type=raw.type,
                    source=raw.source,
                )
            )
            created += 1

    return {"ok": True, "created": created, "updated": updated, "incoming": len(body.events)}
