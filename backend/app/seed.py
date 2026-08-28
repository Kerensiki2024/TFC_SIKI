"""
Données de démonstration — promotion L3GIN (Université de Kinshasa, Faculté Polytechnique).

À chaque démarrage de l’app (lifespan) :
1. Upsert des étudiants + agent avec mots de passe re-hachés.
2. Suppression du compte démo obsolète (alice).
3. Reconstruction des événements de la semaine calendaire courante pour L3GIN
   (supprime d’abord les anciens créneaux de la même fenêtre / sources de test).
"""
from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.demo_accounts import AGENT_PASSWORDS, L3GIN_STUDENTS, STUDENT_PASSWORDS
from app.passwords import hash_password
from app.l3gin_schedule import EVENT_SOURCE, PROMOTION, iter_l3gin_week_events, week_monday
from app.models import Event, Role, User
from app.schedules import TZ, now_local


async def ensure_seed(session: AsyncSession) -> None:
    """Crée / met à jour les comptes L3GIN + agent, puis recharge l'horaire hebdomadaire."""
    # --- Comptes étudiants (liste issue du formulaire L3GIN2025) ---
    for mail, _nom in L3GIN_STUDENTS:
        email = mail.strip().lower()
        plain = STUDENT_PASSWORDS[email]
        r = await session.execute(select(User).where(User.email == email))
        u = r.scalar_one_or_none()
        if u:
            u.role = Role.ETUDIANT.value
            u.groupe = PROMOTION
            u.password_hash = hash_password(plain)
        else:
            session.add(
                User(
                    email=email,
                    role=Role.ETUDIANT.value,
                    groupe=PROMOTION,
                    password_hash=hash_password(plain),
                )
            )

    # --- Compte agent (annulations, démo) ---
    bob_email = "bob.agent@univ.demo"
    bob_plain = AGENT_PASSWORDS[bob_email]
    bob_r = await session.execute(select(User).where(User.email == bob_email))
    bob = bob_r.scalar_one_or_none()
    if not bob:
        session.add(
            User(
                email=bob_email,
                role=Role.AGENT.value,
                groupe=None,
                password_hash=hash_password(bob_plain),
            )
        )
    else:
        bob.password_hash = hash_password(bob_plain)

    # --- Nettoyage ancien compte étudiant démo ---
    legacy = await session.execute(select(User).where(User.email == "alice.etud@univ.demo"))
    legacy_user = legacy.scalar_one_or_none()
    if legacy_user:
        await session.delete(legacy_user)

    await session.flush()

    # Fenêtre temporelle : semaine locale [lundi 00:00, lundi suivant 00:00) en UTC.
    today_local = now_local().date()
    monday = week_monday(today_local)
    next_monday = monday + timedelta(days=7)
    week_start = datetime.combine(monday, time(0, 0), TZ).astimezone(UTC)
    week_end = datetime.combine(next_monday, time(0, 0), TZ).astimezone(UTC)

    # Supprime les cours L3GIN de cette semaine pour les régénérer (idempotence seed).
    await session.execute(
        delete(Event).where(
            Event.date_debut >= week_start,
            Event.date_debut < week_end,
            Event.groupe == PROMOTION,
        )
    )
    await session.execute(delete(Event).where(Event.source == "photo-2026"))
    await session.execute(
        delete(Event).where(Event.groupe.in_(["L3GCI", "L3GEL", "L3GME", "L1-INFO-A"]))
    )

    for item in iter_l3gin_week_events(today_local):
        session.add(Event(**item))
