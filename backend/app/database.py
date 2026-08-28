"""
Moteur SQLAlchemy async et sessions.

Au démarrage : `alembic upgrade head`. Si la base a été créée **avant** Alembic
(tables déjà là), la migration `001_initial` peut échouer : on complète alors
les tables manquantes avec `create_all` et on **stamp** la révision courante.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Classe de base pour tous les modèles ORM (metadata partagée)."""
    pass


def _sync_database_url() -> str:
    return settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")


def _alembic_upgrade_head() -> None:
    root = Path(__file__).resolve().parent.parent
    cfg = Config(str(root / "alembic.ini"))
    sync_url = _sync_database_url()
    sync_engine = create_engine(sync_url)

    try:
        command.upgrade(cfg, "head")
    except ProgrammingError as exc:
        # Base PostgreSQL déjà créée avec create_all (ancienne version) : 001_initial échoue.
        if "already exists" not in str(exc).lower():
            raise
        logger.warning(
            "Alembic 001_initial : tables déjà présentes — complétion schéma + stamp head.",
        )
        import app.models  # noqa: F401 — enregistre toutes les tables sur Base.metadata

        Base.metadata.create_all(sync_engine)
        command.stamp(cfg, "head")


async def init_db() -> None:
    """Applique les migrations Alembic (thread : CLI Alembic synchrone)."""
    await asyncio.to_thread(_alembic_upgrade_head)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dépendance FastAPI : une session par requête, fermée automatiquement."""
    async with SessionLocal() as session:
        yield session
