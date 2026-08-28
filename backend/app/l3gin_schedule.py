"""
Planning unique — promotion L3GIN — Université de Kinshasa, Faculté Polytechnique.

Données : créneaux inspirés des emplois du temps fournis (semestre 2) ; salles A à H en rotation.
Ce module ne touche pas à la base : il produit des dicts passés à Event(...) dans seed.py
et sérialisés pour /n8n/official-feed via official_feed.py.
"""
from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, time, timedelta

from app.schedules import TZ

# Constantes métier réutilisées dans seed, chat, n8n.
PROMOTION = "L3GIN"
INSTITUTION = "Université de Kinshasa, Faculté Polytechnique"
EVENT_SOURCE = "univ-kinshasa-fpoly"

# Huit salles pour répartir les créneaux sans collision fictive répétée.
ROOMS = ["A", "B", "C", "D", "E", "F", "G", "H"]
# Heures locales (fuseau TZ défini dans schedules.py).
SLOTS = [
    (time(8, 30), time(10, 30)),
    (time(10, 30), time(12, 30)),
    (time(14, 0), time(16, 0)),
    (time(16, 0), time(18, 0)),
]

# Cours par jour (lun=0 … sam=5) — colonne L3GIN uniquement ; 4 créneaux = 4 matières max/jour.
DAY_COURSES: dict[int, list[str]] = {
    0: [
        "Travaux de Programmation",
        "Travaux de Programmation",
        "Programmation Orientée Objet",
        "Programmation Orientée Objet",
    ],
    1: [
        "Travaux de Programmation",
        "Travaux de Programmation",
        "Internet Engineering",
        "Internet Engineering",
    ],
    2: [
        "Programmation Orientée Objet",
        "Programmation Orientée Objet",
        "Internet Engineering",
        "Internet Engineering",
    ],
    3: [
        "Travaux de Programmation",
        "Travaux de Programmation",
        "Télécommunications",
        "Télécommunications",
    ],
    4: [
        "Travaux de Programmation",
        "Travaux de Programmation",
        "Internet Engineering",
        "Internet Engineering",
    ],
    5: [
        "Travaux de Programmation",
        "Travaux de Programmation",
        "Télécommunications",
        "Télécommunications",
    ],
}

TEACHERS: dict[str, str] = {
    "Travaux de Programmation": "Prof. Olamba",
    "Programmation Orientée Objet": "CT Kayisu",
    "Internet Engineering": "CT Matalatala & Ass. Mugisha",
    "Télécommunications": "Prof. Mabaya / CT Lufua",
}


def week_monday(ref: date) -> date:
    """Date du lundi de la semaine ISO contenant ref."""
    return ref - timedelta(days=ref.weekday())


def room_for(day_idx: int, slot_idx: int) -> str:
    """Salle dérivée de l’indice jour + slot (rotation sur ROOMS)."""
    return ROOMS[(day_idx + slot_idx) % len(ROOMS)]


def iter_l3gin_week_events(ref_local_date: date) -> Iterator[dict]:
    """
    Itère sur les dicts champs Event pour la semaine calendaire contenant ref_local_date (lun–sam).
    Les datetime sont en UTC pour cohérence avec PostgreSQL timestamptz.
    """
    monday = week_monday(ref_local_date)
    for day_idx in range(6):
        day = monday + timedelta(days=day_idx)
        courses = DAY_COURSES.get(day_idx, DAY_COURSES[0])
        for slot_idx, (t_start, t_end) in enumerate(SLOTS):
            course = courses[slot_idx]
            dt_start = datetime.combine(day, t_start, TZ).astimezone(UTC)
            dt_end = datetime.combine(day, t_end, TZ).astimezone(UTC)
            yield {
                "matiere": course,
                "groupe": PROMOTION,
                "date_debut": dt_start,
                "date_fin": dt_end,
                "salle": room_for(day_idx, slot_idx),
                "enseignant": TEACHERS.get(course, "Enseignant"),
                "type": "cours",
                "source": EVENT_SOURCE,
            }
