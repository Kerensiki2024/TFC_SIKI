"""
JWT (HS256) : création / validation du token, et récupération de l’utilisateur courant
à partir de l’en-tête HTTP Authorization: Bearer <token>.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models import User


def create_access_token(email: str) -> str:
    """Encode un JWT avec le sujet (email) et une date d’expiration."""
    now = datetime.now(UTC)
    payload = {
        "sub": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=settings.jwt_exp_hours)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Décode et vérifie la signature + exp ; lève 401 si token invalide ou expiré."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré.",
        ) from exc


async def get_current_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Dépendance FastAPI : extrait le Bearer, valide le JWT, charge User depuis la DB.
    Utilisée par /auth/me, /chat, et toute route protégée.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise (Bearer token).",
        )
    token = authorization.removeprefix("Bearer ").strip()
    claims = decode_access_token(token)
    email = str(claims.get("sub") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide.")

    r = await session.execute(select(User).where(User.email == email))
    user = r.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur introuvable.")
    return user
