"""
Routes d’authentification : login (vérif mot de passe haché) et profil courant.

Le token JWT est renvoyé au login ; le front le garde et l’envoie en Authorization Bearer.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, get_current_user
from app.database import get_session
from app.models import User
from app.passwords import verify_password
from app.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)):
    """Identifie l’utilisateur et vérifie le mot de passe avec bcrypt (pas de clair en base)."""
    email = body.email.strip().lower()

    r = await session.execute(select(User).where(User.email == email))
    user = r.scalar_one_or_none()
    # Même message pour « email inconnu » et « mauvais mot de passe » (évite l’énumération).
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe invalide.",
        )

    token = create_access_token(user.email)
    return LoginResponse(
        access_token=token,
        email=user.email,
        role=user.role,
        groupe=user.groupe,
    )


@router.get("/me", response_model=LoginResponse)
async def me(user: User = Depends(get_current_user)):
    """
    Retourne l’identité + un nouveau token (démo simple).
    En prod on séparerait souvent « profil » et « refresh token ».
    """
    token = create_access_token(user.email)
    return LoginResponse(
        access_token=token,
        email=user.email,
        role=user.role,
        groupe=user.groupe,
    )
