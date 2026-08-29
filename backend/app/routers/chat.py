"""
Route principale du chatbot : NLU (parse), lecture planning en base,
modifications agent (annuler, déplacer, changer salle, créer) avec confirmation « oui / non ».

- POST /chat exige un JWT (identité = utilisateur connecté, plus d’email dans le corps).
"""
from __future__ import annotations

import json
import unicodedata
from datetime import UTC, datetime, time, timedelta
from typing import Any

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.database import get_session
from app.l3gin_schedule import PROMOTION
from app.models import AuditLog, ChangeRequest, Event, User
from app.nlu import parse
from app.pending_repo import clear_pending, get_pending, save_pending
from app.schedules import TZ, by_subject, day_plan, next_class, now_local, week_plan
from app.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


def _fmt_ev(e: Event) -> str:
    """Une ligne lisible pour l’utilisateur (alignée avec le parsing front des lignes « — »)."""
    start = e.date_debut.astimezone(TZ)
    end = e.date_fin.astimezone(TZ)
    return (
        f"— {e.matiere} ({e.type}), {start.strftime('%a %d/%m %H:%M')}–"
        f"{end.strftime('%H:%M')}, salle {e.salle}, {e.enseignant}"
    )


def _user_groupe(user: User | None) -> str:
    """Groupe pour filtrer les événements : champ user ou promotion par défaut L3GIN."""
    if user and user.groupe:
        return user.groupe
    return PROMOTION


def _shift_event_days(ev: Event, days: int) -> tuple[datetime, datetime]:
    """Décale début et fin du même nombre de jours (fuseau TZ puis UTC)."""
    start_l = ev.date_debut.astimezone(TZ)
    end_l = ev.date_fin.astimezone(TZ)
    delta = timedelta(days=days)
    return (start_l + delta).astimezone(UTC), (end_l + delta).astimezone(UTC)


def _slot_demain_premier_creneau() -> tuple[datetime, datetime]:
    """Créneau démo 08:30–10:30 le lendemain (heure locale du projet)."""
    d = now_local().date() + timedelta(days=1)
    t0 = time(8, 30)
    t1 = time(10, 30)
    dt0 = datetime.combine(d, t0, TZ).astimezone(UTC)
    dt1 = datetime.combine(d, t1, TZ).astimezone(UTC)
    return dt0, dt1


async def _events_ordered(session: AsyncSession, groupe: str) -> list[Event]:
    q = select(Event).where(Event.groupe == groupe).order_by(Event.date_debut.asc())
    r = await session.execute(q)
    return list(r.scalars().all())


def _fold_ascii(s: str) -> str:
    """Minuscules + suppression des accents (pour matcher « Orientee » et « Orientée »)."""
    n = unicodedata.normalize("NFD", s)
    return "".join(c for c in n if unicodedata.category(c) != "Mn").lower()


def _filter_matiere(candidates: list[Event], matiere: str) -> list[Event]:
    ms = _fold_ascii(matiere.strip())
    return [e for e in candidates if ms in _fold_ascii(e.matiere) or not ms]


async def _notify_n8n(intent: str, user_key: str, **payload: Any) -> None:
    body = {"intent": intent, "user": user_key, **payload}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(settings.n8n_webhook_edit, json=body)
    except Exception:
        pass


@router.post("", response_model=ChatResponse)
async def chat_message(
    body: ChatRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    parsed = parse(body.message)
    key = user.email.strip().lower()

    # --- Flux de confirmation : abandon ---
    if parsed.name == "confirm_no":
        await clear_pending(session, key)
        return ChatResponse(reply="D'accord, j'annule cette demande.", intent="confirm_no")

    # --- Flux de confirmation : exécution (annulation, déplacement, salle, création) ---
    pend = await get_pending(session, key) if parsed.name == "confirm_yes" else None
    if parsed.name == "confirm_yes" and pend:
        await clear_pending(session, key)
        kind = pend.get("kind")

        if kind == "annuler":
            ev_id = pend["event_id"]
            r = await session.execute(select(Event).where(Event.id == ev_id))
            ev = r.scalar_one_or_none()
            if not ev:
                return ChatResponse(reply="L'événement n'existe plus en base.", intent="confirm_yes")
            avant = json.dumps(
                {"id": ev.id, "matiere": ev.matiere, "groupe": ev.groupe},
                ensure_ascii=False,
            )
            await session.execute(delete(Event).where(Event.id == ev_id))
            if user:
                session.add(
                    ChangeRequest(
                        intent="annuler",
                        parametres=pend.get("params", {}),
                        statut="approved",
                        utilisateur_demandeur_id=user.id,
                    )
                )
                session.add(
                    AuditLog(
                        action="annuler_cours",
                        valeur_avant=avant,
                        valeur_apres=None,
                        utilisateur_id=user.id,
                    )
                )
            await session.commit()
            await _notify_n8n("annuler", key, event_id=ev_id)
            return ChatResponse(
                reply="Cours annulé et base mise à jour. Les étudiants concernés peuvent être notifiés via n8n.",
                intent="annuler",
                needs_confirmation=False,
            )

        if kind == "deplacer":
            ev_id = pend["event_id"]
            r = await session.execute(select(Event).where(Event.id == ev_id))
            ev = r.scalar_one_or_none()
            if not ev:
                return ChatResponse(reply="L'événement n'existe plus en base.", intent="confirm_yes")
            avant = json.dumps(
                {
                    "id": ev.id,
                    "date_debut": ev.date_debut.isoformat(),
                    "date_fin": ev.date_fin.isoformat(),
                    "salle": ev.salle,
                },
                ensure_ascii=False,
            )
            new_start: datetime = pend["new_date_debut"]
            new_end: datetime = pend["new_date_fin"]
            ev.date_debut = new_start
            ev.date_fin = new_end
            apres = json.dumps(
                {"date_debut": new_start.isoformat(), "date_fin": new_end.isoformat()},
                ensure_ascii=False,
            )
            if user:
                session.add(
                    ChangeRequest(
                        intent="deplacer",
                        parametres=pend.get("params", {}),
                        statut="approved",
                        utilisateur_demandeur_id=user.id,
                    )
                )
                session.add(
                    AuditLog(
                        action="deplacer_cours",
                        valeur_avant=avant,
                        valeur_apres=apres,
                        utilisateur_id=user.id,
                    )
                )
            await session.commit()
            await _notify_n8n("deplacer", key, event_id=ev_id, date_debut=new_start.isoformat())
            return ChatResponse(
                reply=f"Cours déplacé. Nouveau créneau :\n{_fmt_ev(ev)}",
                intent="deplacer",
                needs_confirmation=False,
            )

        if kind == "changer_salle":
            ev_id = pend["event_id"]
            r = await session.execute(select(Event).where(Event.id == ev_id))
            ev = r.scalar_one_or_none()
            if not ev:
                return ChatResponse(reply="L'événement n'existe plus en base.", intent="confirm_yes")
            nouvelle = pend["nouvelle_salle"]
            avant = json.dumps({"id": ev.id, "salle": ev.salle}, ensure_ascii=False)
            ev.salle = nouvelle
            apres = json.dumps({"salle": nouvelle}, ensure_ascii=False)
            if user:
                session.add(
                    ChangeRequest(
                        intent="changer_salle",
                        parametres=pend.get("params", {}),
                        statut="approved",
                        utilisateur_demandeur_id=user.id,
                    )
                )
                session.add(
                    AuditLog(
                        action="changer_salle",
                        valeur_avant=avant,
                        valeur_apres=apres,
                        utilisateur_id=user.id,
                    )
                )
            await session.commit()
            await _notify_n8n("changer_salle", key, event_id=ev_id, salle=nouvelle)
            return ChatResponse(
                reply=f"Salle mise à jour :\n{_fmt_ev(ev)}",
                intent="changer_salle",
                needs_confirmation=False,
            )

        if kind == "creer":
            ne = pend["new_event"]
            ev = Event(**ne)
            session.add(ev)
            if user:
                session.add(
                    ChangeRequest(
                        intent="creer",
                        parametres=pend.get("params", {}),
                        statut="approved",
                        utilisateur_demandeur_id=user.id,
                    )
                )
                session.add(
                    AuditLog(
                        action="creer_cours",
                        valeur_avant=None,
                        valeur_apres=json.dumps(
                            {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in ne.items()},
                            ensure_ascii=False,
                        ),
                        utilisateur_id=user.id,
                    )
                )
            await session.commit()
            await session.refresh(ev)
            await _notify_n8n("creer", key, event_id=ev.id, matiere=ev.matiere)
            return ChatResponse(
                reply=f"Créneau créé :\n{_fmt_ev(ev)}",
                intent="creer",
                needs_confirmation=False,
            )

    role = user.role
    # --- Salutation : message d'accueil adapté au rôle ---
    if parsed.name == "salutation":
        if role in ("AGENT", "RESPONSABLE"):
            exemples = (
                "« Annule le cours de X groupe Y », « Déplace le cours de X demain », "
                "« Mets le cours de X en salle H »"
            )
        else:
            exemples = (
                "« Quel est mon prochain cours ? », « Mes cours aujourd'hui », "
                "« Montre-moi ma semaine »"
            )
        return ChatResponse(
            reply=f"Bonjour ! Je peux t'aider avec les horaires. Essaie par exemple : {exemples}.",
            intent=parsed.name,
        )
    # --- Consultation : prochain cours ---
    if parsed.name == "prochain_cours":
        g = _user_groupe(user)
        ev = await next_class(session, g)
        if not ev:
            return ChatResponse(
                reply="Aucun cours à venir trouvé pour ton groupe.",
                intent=parsed.name,
            )
        return ChatResponse(
            reply=f"Prochain cours : {_fmt_ev(ev)}",
            intent=parsed.name,
        )

    # --- Consultation : journée ---
    if parsed.name == "planning_jour":
        g = _user_groupe(user)
        day = now_local().date()
        evs = await day_plan(session, g, day)
        if not evs:
            return ChatResponse(
                reply="Aucun cours listé pour aujourd'hui.",
                intent=parsed.name,
            )
        lines = "\n".join(_fmt_ev(e) for e in evs)
        return ChatResponse(
            reply=f"Tes cours aujourd'hui :\n{lines}",
            intent=parsed.name,
        )

    # --- Consultation : semaine calendaire ---
    if parsed.name == "planning_semaine":
        g = _user_groupe(user)
        ref = now_local().date()
        evs = await week_plan(session, g, ref)
        if not evs:
            return ChatResponse(reply="Rien de planifié cette semaine.", intent=parsed.name)
        lines = "\n".join(_fmt_ev(e) for e in evs)
        return ChatResponse(
            reply=f"Planning de la semaine :\n{lines}",
            intent=parsed.name,
        )

    # --- Consultation : recherche par matière (filtre texte sur le nom du cours) ---
    if parsed.name == "recherche_matiere":
        g = _user_groupe(user)
        needle = (parsed.params.get("matiere") or "").strip()
        evs = await by_subject(session, g, needle)
        if not evs:
            return ChatResponse(
                reply=f"Aucun créneau trouvé pour « {needle} ».",
                intent=parsed.name,
            )
        lines = "\n".join(_fmt_ev(e) for e in evs)
        return ChatResponse(
            reply=f"Créneaux trouvés :\n{lines}",
            intent=parsed.name,
        )

    # --- Dernières modifications (démo : journal d’audit global, court) ---
    if parsed.name == "notif_changement":
        q = select(AuditLog).order_by(desc(AuditLog.horodatage)).limit(8)
        r = await session.execute(q)
        logs = list(r.scalars().all())
        if not logs:
            return ChatResponse(
                reply="Aucun changement enregistré pour l’instant (audit vide).",
                intent=parsed.name,
            )
        lines = []
        for lg in logs:
            ts = lg.horodatage.astimezone(TZ).strftime("%d/%m %H:%M")
            lines.append(f"— {ts} · {lg.action}")
        return ChatResponse(
            reply="Dernières actions tracées (audit) :\n" + "\n".join(lines),
            intent=parsed.name,
        )

    # --- Modification : annulation (agents seulement) ; confirmation obligatoire ---
    if parsed.name == "annuler":
        if role != "AGENT" and role != "RESPONSABLE":
            return ChatResponse(
                reply="Seuls les agents peuvent annuler un cours. Connecte-toi avec le compte bob.agent@univ.demo.",
                intent=parsed.name,
            )
        groupe = parsed.params.get("groupe") or PROMOTION
        matiere = (parsed.params.get("matiere") or "").strip().lower()
        q = select(Event).where(Event.groupe == groupe).order_by(Event.date_debut.asc())
        r = await session.execute(q)
        candidates = _filter_matiere(list(r.scalars().all()), matiere)
        if not candidates:
            return ChatResponse(
                reply="Je ne trouve pas de cours correspondant. Précise matière et groupe, ex. : "
                "« Annule le cours de Travaux de Programmation groupe L3GIN ».",
                intent=parsed.name,
            )
        if len(candidates) > 1 and not matiere:
            lst = ", ".join(f"{e.matiere} ({e.id})" for e in candidates[:10])
            return ChatResponse(
                reply=f"Plusieurs cours : {lst}. Précise la matière dans ta phrase.",
                intent=parsed.name,
            )
        ev = candidates[0]
        await save_pending(
            session,
            key,
            {
                "kind": "annuler",
                "event_id": ev.id,
                "params": {"groupe": groupe, "matiere": ev.matiere},
            },
        )
        summary = _fmt_ev(ev)
        return ChatResponse(
            reply=(
                "Trouvé :\n"
                f"{summary}\n\n"
                "Pour confirmer l'annulation, réponds exactement « oui ». "
                "Pour abandonner : « non »."
            ),
            intent=parsed.name,
            needs_confirmation=True,
        )

    # --- Déplacement de créneau (agent) : confirmation ---
    if parsed.name == "deplacer":
        if role != "AGENT" and role != "RESPONSABLE":
            return ChatResponse(
                reply="Seuls les agents peuvent déplacer un cours. Utilise le compte bob.agent@univ.demo.",
                intent=parsed.name,
            )
        groupe = (parsed.params.get("groupe") or PROMOTION) if isinstance(parsed.params, dict) else PROMOTION
        matiere = (parsed.params.get("matiere") or "").strip().lower() if isinstance(parsed.params, dict) else ""
        offset = int(parsed.params.get("offset_jours") or 1) if isinstance(parsed.params, dict) else 1
        offset = max(1, min(offset, 30))
        all_e = await _events_ordered(session, groupe)
        candidates = _filter_matiere(all_e, matiere)
        if not candidates:
            return ChatResponse(
                reply="Je ne trouve pas de cours. Exemple : « Déplace le cours de Travaux de Programmation demain ».",
                intent=parsed.name,
            )
        if len(candidates) > 1 and not matiere:
            lst = ", ".join(f"{e.matiere} ({e.id})" for e in candidates[:10])
            return ChatResponse(
                reply=f"Plusieurs cours : {lst}. Précise la matière.",
                intent=parsed.name,
            )
        ev = candidates[0]
        new_start, new_end = _shift_event_days(ev, offset)
        ns, ne = new_start.astimezone(TZ), new_end.astimezone(TZ)
        summary_old = _fmt_ev(ev)
        summary_new = (
            f"— {ev.matiere} ({ev.type}), {ns.strftime('%a %d/%m %H:%M')}–{ne.strftime('%H:%M')}, "
            f"salle {ev.salle}, {ev.enseignant}"
        )
        await save_pending(
            session,
            key,
            {
                "kind": "deplacer",
                "event_id": ev.id,
                "new_date_debut": new_start,
                "new_date_fin": new_end,
                "params": {"groupe": groupe, "matiere": ev.matiere, "offset_jours": offset},
            },
        )
        return ChatResponse(
            reply=(
                f"Déplacement proposé (+{offset} jour(s)) :\n"
                f"Avant : {summary_old}\n"
                f"Après : {summary_new}\n\n"
                "Réponds « oui » pour confirmer, « non » pour annuler."
            ),
            intent=parsed.name,
            needs_confirmation=True,
        )

    # --- Changement de salle (agent) : confirmation ---
    if parsed.name == "changer_salle":
        if role != "AGENT" and role != "RESPONSABLE":
            return ChatResponse(
                reply="Seuls les agents peuvent changer une salle. Utilise le compte bob.agent@univ.demo.",
                intent=parsed.name,
            )
        nouvelle = (parsed.params.get("nouvelle_salle") or "").strip().upper() if isinstance(parsed.params, dict) else ""
        if not nouvelle:
            return ChatResponse(
                reply="Indique la salle cible, ex. : « Mets le cours de Programmation Orientée Objet en salle H ».",
                intent=parsed.name,
            )
        groupe = (parsed.params.get("groupe") or PROMOTION) if isinstance(parsed.params, dict) else PROMOTION
        matiere = (parsed.params.get("matiere") or "").strip().lower() if isinstance(parsed.params, dict) else ""
        all_e = await _events_ordered(session, groupe)
        candidates = _filter_matiere(all_e, matiere)
        if not candidates:
            return ChatResponse(
                reply="Je ne trouve pas de cours pour ce groupe / cette matière.",
                intent=parsed.name,
            )
        if len(candidates) > 1 and not matiere:
            lst = ", ".join(f"{e.matiere} ({e.id})" for e in candidates[:10])
            return ChatResponse(
                reply=f"Plusieurs cours : {lst}. Précise la matière.",
                intent=parsed.name,
            )
        ev = candidates[0]
        await save_pending(
            session,
            key,
            {
                "kind": "changer_salle",
                "event_id": ev.id,
                "nouvelle_salle": nouvelle,
                "params": {"groupe": groupe, "matiere": ev.matiere, "nouvelle_salle": nouvelle},
            },
        )
        summary = _fmt_ev(ev)
        return ChatResponse(
            reply=(
                f"Changement de salle proposé : {ev.salle} → {nouvelle}\n"
                f"{summary}\n\n"
                "Réponds « oui » pour confirmer, « non » pour annuler."
            ),
            intent=parsed.name,
            needs_confirmation=True,
        )

    # --- Création de créneau (agent) : confirmation ---
    if parsed.name == "creer":
        if role != "AGENT" and role != "RESPONSABLE":
            return ChatResponse(
                reply="Seuls les agents peuvent créer un créneau. Utilise le compte bob.agent@univ.demo.",
                intent=parsed.name,
            )
        matiere_raw = (parsed.params.get("matiere") or "").strip() if isinstance(parsed.params, dict) else ""
        if not matiere_raw:
            return ChatResponse(
                reply="Indique la matière, ex. : « Crée un cours de Séminaire recherche salle B ».",
                intent=parsed.name,
            )
        groupe = (parsed.params.get("groupe") or PROMOTION) if isinstance(parsed.params, dict) else PROMOTION
        salle = (parsed.params.get("nouvelle_salle") or "A").strip().upper() if isinstance(parsed.params, dict) else "A"
        dt0, dt1 = _slot_demain_premier_creneau()
        new_event = {
            "matiere": matiere_raw,
            "groupe": groupe,
            "date_debut": dt0,
            "date_fin": dt1,
            "salle": salle,
            "enseignant": "À préciser",
            "type": "cours",
            "source": "agent-chat",
        }
        await save_pending(
            session,
            key,
            {
                "kind": "creer",
                "new_event": new_event,
                "params": {"groupe": groupe, "matiere": matiere_raw, "salle": salle},
            },
        )
        preview = (
            f"— {matiere_raw} (cours), {dt0.astimezone(TZ).strftime('%a %d/%m %H:%M')}–"
            f"{dt1.astimezone(TZ).strftime('%H:%M')}, salle {salle}, À préciser"
        )
        return ChatResponse(
            reply=(
                "Nouveau créneau proposé (demain 08:30–10:30, fuseau Europe/Paris) :\n"
                f"{preview}\n"
                f"Groupe : {groupe}\n\n"
                "Réponds « oui » pour créer en base, « non » pour annuler."
            ),
            intent=parsed.name,
            needs_confirmation=True,
        )

    # --- Intent NLU non reconnu ---
    return ChatResponse(
        reply=(
            "Je n'ai pas compris. Essaie par exemple : « Quel est mon prochain cours ? », "
            "« Mes cours aujourd'hui », ou « Montre-moi ma semaine »."
        ),
        intent="unknown",
    )
