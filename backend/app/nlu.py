"""
NLU par règles (mots-clés + regex) — priorité : prévisibilité pour le mémoire, pas le rappel maximal.

Flux : message brut → ParsedIntent { name, params } utilisé par routers/chat.py.
L’ordre des tests compte : les intentions « action agent » (annuler, déplacer, …) passent
avant « recherche_matière », sinon « cours » déclencherait une fausse recherche.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedIntent:
    """Résultat du parseur : nom d’intention + paramètres extraits + message original."""
    name: str
    params: dict[str, Any] = field(default_factory=dict)
    raw_message: str = ""


_CONFIRM_YES = re.compile(
    r"^\s*(oui|ok|confirme|valide|d\W*accord|yes)\s*[!.?]?\s*$",
    re.I,
)
_CONFIRM_NO = re.compile(
    r"^\s*(non|annul|stop|erreur)\s*[!.?]?\s*$",
    re.I,
)


def _groupe_matiere_from_phrase(text: str, low_text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    g = re.search(r"groupe\s+([A-Z0-9\-]+)|\b(L\d[\w\-]+)\b", text, re.I)
    if g:
        out["groupe"] = (g.group(1) or g.group(2)).upper()
    mat2 = re.search(
        r"cours\s+de\s+([^\n,]+?)(?:\s+groupe|\s+demain|\s+prévu|\s+à|\s+en\s+salle|\s+salle|\s*$)",
        low_text,
    )
    if not mat2:
        mat2 = re.search(r"cours\s+de\s+([\wÀ-ÖØ-öø-\u036f]+\s*\d*)", text, re.I)
    if mat2:
        out["matiere"] = mat2.group(1).strip().rstrip(".").strip()
    return out


def _offset_deplacement(low_text: str) -> int:
    if re.search(r"\baprès[- ]demain|dans\s+2\s*jours", low_text):
        return 2
    if re.search(r"\bdemain\b", low_text):
        return 1
    if re.search(r"\b(semaine\s+prochaine|dans\s+une\s+semaine|7\s*jours)\b", low_text):
        return 7
    m = re.search(r"dans\s+(\d{1,2})\s*jours?", low_text)
    if m:
        return min(int(m.group(1)), 30)
    return 1


def _nouvelle_salle(low_text: str) -> str | None:
    sm = re.search(r"(?:salle|en)\s*([A-H])\b", low_text, re.I)
    if sm:
        return sm.group(1).upper()
    return None


def parse(message: str) -> ParsedIntent:
    """
    Classifie le texte utilisateur. Les regex sont volontairement simples (démo).
    Extensions possibles : entités dates, fuzzy match matières, modèle ML.
    """
    m = message.strip()
    low = m.lower()

    if _CONFIRM_YES.match(m):
        return ParsedIntent("confirm_yes", {}, m)
    if _CONFIRM_NO.match(m):
        return ParsedIntent("confirm_no", {}, m)

    if re.search(
        r"\b(quel est )?mon prochain cours|prochain cours|après c'est quoi|next class",
        low,
    ):
        return ParsedIntent("prochain_cours", {}, m)

    if re.search(r"\bcours?\s+aujourd'hui|planning du jour|mes cours aujourd|today\b", low):
        return ParsedIntent("planning_jour", {}, m)

    if re.search(r"semaine|week|planning de la semaine|ma semaine", low):
        return ParsedIntent("planning_semaine", {}, m)

    # --- Modifications (avant recherche_matiere : évite le faux positif sur le mot « cours ») ---
    if re.search(r"annul|cancel|supprim", low):
        return ParsedIntent("annuler", _groupe_matiere_from_phrase(m, low), m)

    if re.search(r"d[ée]cal|d[ée]plac|move|changer?\s+(?:le\s+)?jour", low):
        params = _groupe_matiere_from_phrase(m, low)
        params["offset_jours"] = _offset_deplacement(low)
        return ParsedIntent("deplacer", params, m)

    if re.search(r"salle|room", low) and re.search(r"mets|mettre|change", low):
        params = _groupe_matiere_from_phrase(m, low)
        ns = _nouvelle_salle(low)
        if ns:
            params["nouvelle_salle"] = ns
        return ParsedIntent("changer_salle", params, m)

    if re.search(r"cr[ée]{1,2}e(?!r)(?: un)?\s+cours|nouveau cours|add class", low):
        params: dict[str, Any] = {}
        g = re.search(r"groupe\s+([A-Z0-9\-]+)|\b(L\d[\w\-]+)\b", m, re.I)
        if g:
            params["groupe"] = (g.group(1) or g.group(2)).upper()
        mat3 = re.search(
            r"(?:cours\s+de|cr[ée]{1,2}e(?:\s+un)?\s+cours\s+de)\s+([^\n,.;]+?)(?:\s+groupe|\s+salle|\s+demain|\s*$)",
            low,
        )
        if mat3:
            params["matiere"] = mat3.group(1).strip().rstrip(".").strip()
        ns = _nouvelle_salle(low)
        if ns:
            params["nouvelle_salle"] = ns
        if re.search(r"\bdemain\b", low):
            params["demain"] = True
        return ParsedIntent("creer", params, m)

    # Question « quand / où » sur une matière
    mat = re.search(
        r"cours(?:\s+de)?\s+['\"]?([^'\"?\n.]+)['\"]?|"
        r"quand\s+(?:est|a)\s+(?:le\s+)?(?:cours\s+de\s+)?([^\n?.]+)",
        m,
        re.I,
    )
    if mat and re.search(
        r"\b(où|quand|jour|heure|matière|matiere|salle|cours)\b",
        low,
    ):
        topic = (mat.group(1) or mat.group(2) or "").strip()
        topic = re.sub(r"\s+", " ", topic)
        if topic and len(topic) < 120:
            return ParsedIntent("recherche_matiere", {"matiere": topic}, m)

    if re.search(r"notification|chang(e|ement)|reçu", low):
        return ParsedIntent("notif_changement", {}, m)

    return ParsedIntent("unknown", {}, m)
