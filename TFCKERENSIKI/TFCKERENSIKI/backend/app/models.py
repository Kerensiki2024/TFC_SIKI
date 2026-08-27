"""
Modèles SQLAlchemy : users, events, change_requests, audit_logs, pending_confirmations.
Les enums Python servent surtout de référence pour les chaînes stockées en base.
"""
import enum
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Role(str, enum.Enum):
    """Rôles métier : étudiant, agent scolarité, responsable pédagogique."""
    ETUDIANT = "ETUDIANT"
    AGENT = "AGENT"
    RESPONSABLE = "RESPONSABLE"


class ChangeStatus(str, enum.Enum):
    """Cycle de vie d’une demande de modification (workflow futur)."""
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class User(Base):
    """Compte applicatif : email unique, rôle, groupe (promotion), mot de passe haché."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(32))
    groupe: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # bcrypt (passlib) ; nullable pour compat anciennes lignes, le login refuse si vide.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Event(Base):
    """Créneau cours / examen affiché par le chatbot."""
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    matiere: Mapped[str] = mapped_column(String(255))
    groupe: Mapped[str] = mapped_column(String(64), index=True)
    date_debut: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    date_fin: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    salle: Mapped[str] = mapped_column(String(64))
    enseignant: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(32))
    # Origine des données : démo seed, source « officielle », n8n, etc.
    source: Mapped[str] = mapped_column(String(64), default="demo")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ChangeRequest(Base):
    """Trace d’une intention de modification (ex. annulation) liée à un utilisateur."""
    __tablename__ = "change_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    intent: Mapped[str] = mapped_column(String(64))
    parametres: Mapped[dict[str, Any]] = mapped_column(JSON)
    statut: Mapped[str] = mapped_column(String(32), default=ChangeStatus.pending.value)
    utilisateur_demandeur_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    date_demande: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship()


class AuditLog(Base):
    """Journal append-only pour conformité / démo (qui a fait quoi, avant/après)."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(128))
    valeur_avant: Mapped[str | None] = mapped_column(Text, nullable=True)
    valeur_apres: Mapped[str | None] = mapped_column(Text, nullable=True)
    utilisateur_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    horodatage: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PendingConfirmation(Base):
    """File d’attente des actions agent en attente de « oui » (survit au redémarrage de l’API)."""
    __tablename__ = "pending_confirmations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
