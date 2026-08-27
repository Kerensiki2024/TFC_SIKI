"""
Comptes démo — promotion L3GIN (réponses formulaire).

Convention mot de passe étudiant : <Nom>@123 où Nom est la colonne famille du formulaire.
Ces chaînes en clair ne servent qu’au seed : en base on enregistre uniquement password_hash.
"""
from __future__ import annotations

# (email Google du formulaire, nom de famille pour construire le mot de passe)
L3GIN_STUDENTS: list[tuple[str, str]] = [
    ("sharobukasa2003@gmail.com", "Mukanya"),
    ("kerensiki@gmail.com", "Makula"),
    ("arthesluzolo@gmail.com", "LUZOLO"),
    ("munsingiele@gmail.com", "MUNSINGIELE"),
    ("kandololucie6@gmail.com", "Kandolo"),
    ("thaddeemukenge@gmail.com", "MUKENGE"),
    ("epaphrasmakenene@gmail.com", "MAKENENE"),
    ("michaellumu25@gmail.com", "LUMU"),
    ("hermesmbizi@gmail.com", "Nzuzi"),
    ("bampirengabo@gmail.com", "BAMPIRE"),
    ("mpombolo00@gmail.com", "MPOMBOLO"),
]

# email (minuscules) → mot de passe en clair connu du seed uniquement
STUDENT_PASSWORDS: dict[str, str] = {
    email.strip().lower(): f"{nom}@123" for email, nom in L3GIN_STUDENTS
}

# Agent scolarité (démo) — même principe : clair au seed, hash en base
AGENT_PASSWORDS: dict[str, str] = {
    "bob.agent@univ.demo": "bob123",
}

# Regroupement pratique si besoin d’itérer tous les mots de passe « sources » (tests, doc).
ALL_PLAINTEXT_PASSWORDS: dict[str, str] = {**STUDENT_PASSWORDS, **AGENT_PASSWORDS}
