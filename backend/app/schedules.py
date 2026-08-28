"""
Requêtes SQLAlchemy sur la table events : consultation par groupe / jour / semaine / matière.

Fuseau TZ : Europe/Paris (aligné n8n GENERIC_TIMEZONE) — les instants en base sont en UTC.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event


TZ = ZoneInfo("Europe/Paris")


def now_local() -> datetime:
    """Horloge « locale » du projet (affichages utilisateur)."""
    return datetime.now(TZ)


def week_bounds(d: date) -> tuple[datetime, datetime]:
    """Début (lundi 00:00) et fin (lundi suivant 00:00) de la semaine contenant d, en TZ locale."""
    start = datetime.combine(d - timedelta(days=d.weekday()), datetime.min.time(), TZ)
    end = start + timedelta(days=7)
    return start, end


async def next_class(session: AsyncSession, groupe: str) -> Event | None:
    """Premier événement du groupe dont la fin est encore dans le futur."""
    n = now_local().astimezone(UTC)
    q = (
        select(Event)
        .where(
            and_(
                Event.groupe == groupe,
                Event.date_fin > n,
            )
        )
        .order_by(Event.date_debut.asc())
        .limit(1)
    )
    r = await session.execute(q)
    return r.scalar_one_or_none()


async def day_plan(session: AsyncSession, groupe: str, day: date) -> list[Event]:
    """Tous les cours du jour calendaire `day` pour le groupe (bornes converties en UTC)."""
    start = datetime.combine(day, datetime.min.time(), TZ)
    end = start + timedelta(days=1)
    q = (
        select(Event)
        .where(
            and_(
                Event.groupe == groupe,
                Event.date_debut >= start.astimezone(UTC),
                Event.date_debut < end.astimezone(UTC),
            )
        )
        .order_by(Event.date_debut.asc())
    )
    r = await session.execute(q)
    return list(r.scalars().all())


async def week_plan(session: AsyncSession, groupe: str, ref: date) -> list[Event]:
    """Planning de la semaine calendaire contenant ref (lundi → dimanche suivant exclus en logique bounds)."""
    start, end = week_bounds(ref)
    q = (
        select(Event)
        .where(
            and_(
                Event.groupe == groupe,
                Event.date_debut >= start.astimezone(UTC),
                Event.date_debut < end.astimezone(UTC),
            )
        )
        .order_by(Event.date_debut.asc())
    )
    r = await session.execute(q)
    return list(r.scalars().all())


async def by_subject(session: AsyncSession, groupe: str, needle: str) -> list[Event]:
    """Filtre en Python sur le nom de matière (sous-chaîne insensible à la casse)."""
    needle = needle.lower()
    q = (
        select(Event)
        .where(Event.groupe == groupe)
        .order_by(Event.date_debut.asc())
    )
    r = await session.execute(q)
    out = []
    for ev in r.scalars().all():
        if needle in ev.matiere.lower():
            out.append(ev)
    return out
