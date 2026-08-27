"""Schéma hérité : colonnes / tables manquantes après ancienne base create_all + stamp.

Revision ID: 002_legacy_compat
Revises: 001_initial
Create Date: 2026-05-12

"""
from typing import Sequence, Union

from alembic import op

revision: str = "002_legacy_compat"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ancienne table users sans bcrypt
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255) NULL",
    )
    # Table confirmations (si stamp a sauté la création)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pending_confirmations (
            id SERIAL NOT NULL PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL,
            payload JSON NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """,
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_pending_confirmations_user_email "
        "ON pending_confirmations (user_email)",
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_pending_confirmations_user_email")
    op.execute("DROP TABLE IF EXISTS pending_confirmations")
    op.drop_column("users", "password_hash")
