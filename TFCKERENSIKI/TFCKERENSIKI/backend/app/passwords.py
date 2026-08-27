"""
Hachage des mots de passe (bcrypt via passlib) — stockage sécurisé en base (point 2 backend).

- On ne stocke jamais le mot de passe en clair.
- bcrypt tronque les entrées très longues : on limite à 72 octets côté appel (convention passlib).
"""
from __future__ import annotations

from passlib.context import CryptContext

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Retourne une chaîne bcrypt à enregistrer dans users.password_hash."""
    return _pwd.hash(plain[:72])


def verify_password(plain: str, password_hash: str | None) -> bool:
    """True si le mot de passe correspond au hash ; False si pas de hash ou mismatch."""
    if not password_hash:
        return False
    return _pwd.verify(plain[:72], password_hash)
