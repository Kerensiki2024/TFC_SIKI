"""Schéma initial (users, events, change_requests, audit_logs, pending_confirmations).

Revision ID: 001_initial
Revises:
Create Date: 2026-02-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("groupe", sa.String(64), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("matiere", sa.String(255), nullable=False),
        sa.Column("groupe", sa.String(64), nullable=False),
        sa.Column("date_debut", sa.DateTime(timezone=True), nullable=False),
        sa.Column("date_fin", sa.DateTime(timezone=True), nullable=False),
        sa.Column("salle", sa.String(64), nullable=False),
        sa.Column("enseignant", sa.String(255), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_events_groupe"), "events", ["groupe"], unique=False)

    op.create_table(
        "change_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("intent", sa.String(64), nullable=False),
        sa.Column("parametres", sa.JSON(), nullable=False),
        sa.Column("statut", sa.String(32), nullable=False),
        sa.Column("utilisateur_demandeur_id", sa.Integer(), nullable=False),
        sa.Column("date_demande", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["utilisateur_demandeur_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("valeur_avant", sa.Text(), nullable=True),
        sa.Column("valeur_apres", sa.Text(), nullable=True),
        sa.Column("utilisateur_id", sa.Integer(), nullable=True),
        sa.Column("horodatage", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["utilisateur_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "pending_confirmations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_email", sa.String(255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pending_confirmations_user_email"), "pending_confirmations", ["user_email"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_pending_confirmations_user_email"), table_name="pending_confirmations")
    op.drop_table("pending_confirmations")
    op.drop_table("audit_logs")
    op.drop_table("change_requests")
    op.drop_index(op.f("ix_events_groupe"), table_name="events")
    op.drop_table("events")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
