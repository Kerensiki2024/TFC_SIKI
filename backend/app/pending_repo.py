"""Sérialisation et persistance des confirmations chat (remplace l’ancien dict en mémoire)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PendingConfirmation


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_dt(val: str | datetime) -> datetime:
    if isinstance(val, datetime):
        return val
    s = val.replace("Z", "+00:00") if isinstance(val, str) else val
    return datetime.fromisoformat(s)


def pend_to_storable(pend: dict[str, Any]) -> dict[str, Any]:
    """Convertit le dict métier en JSON-friendly (datetime → ISO)."""
    out: dict[str, Any] = {}
    for k, v in pend.items():
        if k == "new_event" and isinstance(v, dict):
            ne: dict[str, Any] = {}
            for nk, nv in v.items():
                ne[nk] = _iso(nv) if isinstance(nv, datetime) else nv
            out[k] = ne
        elif isinstance(v, datetime):
            out[k] = _iso(v)
        else:
            out[k] = v
    return out


def pend_from_storable(d: dict[str, Any]) -> dict[str, Any]:
    """Reconstruit le dict métier (ISO → datetime là où il faut)."""
    out = dict(d)
    for key in ("new_date_debut", "new_date_fin"):
        if key in out and isinstance(out[key], str):
            out[key] = _parse_dt(out[key])
    if out.get("kind") == "creer" and isinstance(out.get("new_event"), dict):
        ne = dict(out["new_event"])
        for dk in ("date_debut", "date_fin"):
            if dk in ne and isinstance(ne[dk], str):
                ne[dk] = _parse_dt(ne[dk])
        out["new_event"] = ne
    return out


async def get_pending(session: AsyncSession, user_email: str) -> dict[str, Any] | None:
    key = user_email.strip().lower()
    r = await session.execute(select(PendingConfirmation).where(PendingConfirmation.user_email == key))
    row = r.scalar_one_or_none()
    if not row:
        return None
    return pend_from_storable(dict(row.payload))


async def save_pending(session: AsyncSession, user_email: str, pend: dict[str, Any]) -> None:
    key = user_email.strip().lower()
    st = pend_to_storable(pend)
    await session.execute(delete(PendingConfirmation).where(PendingConfirmation.user_email == key))
    session.add(PendingConfirmation(user_email=key, payload=st))
    await session.commit()


async def clear_pending(session: AsyncSession, user_email: str) -> None:
    key = user_email.strip().lower()
    await session.execute(delete(PendingConfirmation).where(PendingConfirmation.user_email == key))
    await session.commit()
