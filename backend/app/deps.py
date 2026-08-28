"""
Dépendances FastAPI réutilisables : contrôle d’accès par rôle (RBAC simple).

Exemple d’usage sur une route :
    user: User = Depends(require_agent)
"""
from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.auth import get_current_user
from app.models import User


def require_roles(*allowed: str) -> Callable[..., User]:
    """
    Fabrique une dépendance qui refuse (403) si user.role n’est pas dans allowed.
    `allowed` contient les valeurs string stockées en base (ex. "AGENT").
    """

    async def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Droits insuffisants pour cette opération.",
            )
        return user

    return _dep


# Raccourci : agent scolarité ou niveau responsable.
require_agent = require_roles("AGENT", "RESPONSABLE")
