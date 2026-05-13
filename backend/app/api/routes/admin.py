from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.proposed_change import ProposedChange
from app.models.user import RoleEnum, User
from app.schemas.admin import (
    CancelEventRequest,
    DecisionRequest,
    EventCreateRequest,
    MoveEventRequest,
    ProposedChangeOut,
)
from app.schemas.event import EventOut
from app.services.admin_service import (
    approve_or_reject_change,
    cancel_event,
    create_event,
    event_to_out,
    move_event,
)

router = APIRouter()


@router.post("/events", response_model=EventOut)
def create_event_endpoint(
    payload: EventCreateRequest,
    current_user: User = Depends(require_roles(RoleEnum.STAFF, RoleEnum.DIRECTOR)),
    db: Session = Depends(get_db),
):
    event = create_event(db=db, payload=payload, current_user=current_user)
    return event_to_out(event)


@router.post("/events/{event_id}/cancel")
def cancel_event_endpoint(
    event_id: int,
    payload: CancelEventRequest,
    current_user: User = Depends(require_roles(RoleEnum.STAFF, RoleEnum.DIRECTOR)),
    db: Session = Depends(get_db),
):
    result = cancel_event(db=db, event_id=event_id, payload=payload, current_user=current_user)
    return result


@router.post("/events/{event_id}/move")
def move_event_endpoint(
    event_id: int,
    payload: MoveEventRequest,
    current_user: User = Depends(require_roles(RoleEnum.STAFF, RoleEnum.DIRECTOR)),
    db: Session = Depends(get_db),
):
    result = move_event(db=db, event_id=event_id, payload=payload, current_user=current_user)
    return result


@router.get("/proposed-changes", response_model=list[ProposedChangeOut])
def list_proposed_changes(
    current_user: User = Depends(require_roles(RoleEnum.DIRECTOR, RoleEnum.STAFF)),
    db: Session = Depends(get_db),
):
    stmt = select(ProposedChange).order_by(ProposedChange.created_at.desc())
    items = db.execute(stmt).scalars().all()
    return [
        ProposedChangeOut(
            id=item.id,
            action_type=item.action_type,
            payload=item.payload,
            is_sensitive=item.is_sensitive,
            status=item.status.value,
            created_at=item.created_at,
        )
        for item in items
    ]


@router.post("/proposed-changes/{change_id}/decision")
def decide_proposed_change(
    change_id: int,
    payload: DecisionRequest,
    current_user: User = Depends(require_roles(RoleEnum.DIRECTOR)),
    db: Session = Depends(get_db),
):
    result = approve_or_reject_change(db=db, change_id=change_id, payload=payload, current_user=current_user)
    if not result:
        raise HTTPException(status_code=404, detail="Proposed change not found")
    return result
