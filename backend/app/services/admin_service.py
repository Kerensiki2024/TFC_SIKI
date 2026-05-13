from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.audit_log import AuditLog
from app.models.course import Course
from app.models.event import Event, EventStatusEnum, EventTypeEnum
from app.models.group import AcademicGroup
from app.models.notification import Notification
from app.models.proposed_change import ProposedChange, ProposedChangeStatusEnum
from app.models.room import Room
from app.models.user import RoleEnum, User
from app.schemas.admin import CancelEventRequest, DecisionRequest, EventCreateRequest, MoveEventRequest
from app.schemas.event import EventOut
from app.services.n8n_service import trigger_webhook
from app.services.student_service import event_to_out


def _get_event_or_404(db: Session, event_id: int) -> Event:
    stmt = (
        select(Event)
        .options(joinedload(Event.course), joinedload(Event.group), joinedload(Event.room))
        .where(Event.id == event_id)
    )
    event = db.execute(stmt).scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event



def _ensure_refs_exist(db: Session, payload: EventCreateRequest) -> tuple[Course, AcademicGroup, Room]:
    course = db.get(Course, payload.course_id)
    group = db.get(AcademicGroup, payload.group_id)
    room = db.get(Room, payload.room_id)
    if not course or not group or not room:
        raise HTTPException(status_code=400, detail="Invalid course_id, group_id or room_id")
    return course, group, room



def _create_audit(db: Session, *, action: str, user_id: int, event_id: int | None, old_value: dict | None, new_value: dict | None, reason: str | None = None) -> None:
    audit = AuditLog(
        action=action,
        user_id=user_id,
        event_id=event_id,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
    )
    db.add(audit)



def _notify_group_users(db: Session, group_id: int, title: str, message: str) -> None:
    stmt = select(User).where(User.group_id == group_id)
    users = db.execute(stmt).scalars().all()
    for user in users:
        db.add(Notification(user_id=user.id, title=title, message=message))

    trigger_webhook(
        settings.N8N_NOTIFICATION_WEBHOOK_URL,
        {
            "group_id": group_id,
            "title": title,
            "message": message,
            "created_at": datetime.utcnow().isoformat(),
        },
    )



def create_event(db: Session, payload: EventCreateRequest, current_user: User) -> Event:
    course, group, room = _ensure_refs_exist(db, payload)
    event_type = EventTypeEnum(payload.type)

    event = Event(
        course_id=course.id,
        group_id=group.id,
        room_id=room.id,
        teacher_name=payload.teacher_name,
        type=event_type,
        start_time=payload.start_time,
        end_time=payload.end_time,
        status=EventStatusEnum.SCHEDULED,
    )
    db.add(event)
    db.flush()
    db.refresh(event)

    _create_audit(
        db,
        action="CREATE_EVENT",
        user_id=current_user.id,
        event_id=event.id,
        old_value=None,
        new_value={
            "course_id": event.course_id,
            "group_id": event.group_id,
            "room_id": event.room_id,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat(),
        },
    )
    db.commit()
    db.refresh(event)
    return _get_event_or_404(db, event.id)



def cancel_event(db: Session, event_id: int, payload: CancelEventRequest, current_user: User) -> dict:
    event = _get_event_or_404(db, event_id)
    old_state = {
        "status": event.status.value,
        "reason": event.reason,
    }

    event.status = EventStatusEnum.CANCELLED
    event.reason = payload.reason

    _create_audit(
        db,
        action="CANCEL_EVENT",
        user_id=current_user.id,
        event_id=event.id,
        old_value=old_state,
        new_value={"status": event.status.value, "reason": event.reason},
        reason=payload.reason,
    )

    db.add(event)
    db.commit()

    _notify_group_users(
        db,
        group_id=event.group_id,
        title="Cours annulé",
        message=f"Le cours {event.course.name} prévu le {event.start_time} est annulé. Raison: {payload.reason}",
    )
    db.commit()

    trigger_webhook(
        settings.N8N_EDITION_WEBHOOK_URL,
        {
            "intent": "CANCEL_EVENT",
            "event_id": event.id,
            "requested_by": current_user.id,
            "role": current_user.role.value,
            "reason": payload.reason,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )

    return {"status": "applied", "event_id": event.id, "message": "Event cancelled successfully"}



def move_event(db: Session, event_id: int, payload: MoveEventRequest, current_user: User) -> dict:
    event = _get_event_or_404(db, event_id)
    is_sensitive = event.type == EventTypeEnum.EXAMEN or abs((payload.new_start_time - event.start_time).days) >= 7

    contract_payload = {
        "event_id": event.id,
        "old_start_time": event.start_time.isoformat(),
        "old_end_time": event.end_time.isoformat(),
        "new_start_time": payload.new_start_time.isoformat(),
        "new_end_time": payload.new_end_time.isoformat(),
        "new_room_id": payload.new_room_id,
        "reason": payload.reason,
    }

    if is_sensitive:
        proposed = ProposedChange(
            action_type="MOVE_EVENT",
            payload=contract_payload,
            is_sensitive=True,
            event_id=event.id,
            requested_by=current_user.id,
            status=ProposedChangeStatusEnum.PENDING,
        )
        db.add(proposed)
        _create_audit(
            db,
            action="PROPOSE_MOVE_EVENT",
            user_id=current_user.id,
            event_id=event.id,
            old_value=None,
            new_value=contract_payload,
            reason=payload.reason,
        )
        db.commit()

        trigger_webhook(
            settings.N8N_EDITION_WEBHOOK_URL,
            {
                "intent": "MOVE_EVENT",
                "sensitive": True,
                "requested_by": current_user.id,
                "role": current_user.role.value,
                **contract_payload,
            },
        )
        return {
            "status": "pending_approval",
            "message": "Sensitive change stored for director approval",
        }

    old_state = {
        "start_time": event.start_time.isoformat(),
        "end_time": event.end_time.isoformat(),
        "room_id": event.room_id,
    }
    event.start_time = payload.new_start_time
    event.end_time = payload.new_end_time
    if payload.new_room_id:
        if not db.get(Room, payload.new_room_id):
            raise HTTPException(status_code=400, detail="Invalid new_room_id")
        event.room_id = payload.new_room_id
    event.status = EventStatusEnum.MOVED
    event.reason = payload.reason

    _create_audit(
        db,
        action="MOVE_EVENT",
        user_id=current_user.id,
        event_id=event.id,
        old_value=old_state,
        new_value={
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat(),
            "room_id": event.room_id,
        },
        reason=payload.reason,
    )
    db.add(event)
    db.commit()

    _notify_group_users(
        db,
        group_id=event.group_id,
        title="Cours déplacé",
        message=f"Le cours {event.course.name} a été déplacé au {event.start_time}.",
    )
    db.commit()

    trigger_webhook(
        settings.N8N_EDITION_WEBHOOK_URL,
        {
            "intent": "MOVE_EVENT",
            "sensitive": False,
            "requested_by": current_user.id,
            "role": current_user.role.value,
            **contract_payload,
        },
    )
    return {"status": "applied", "event_id": event.id, "message": "Event moved successfully"}



def approve_or_reject_change(db: Session, change_id: int, payload: DecisionRequest, current_user: User) -> dict | None:
    change = db.get(ProposedChange, change_id)
    if not change:
        return None
    if change.status != ProposedChangeStatusEnum.PENDING:
        raise HTTPException(status_code=400, detail="Change already decided")

    change.decided_at = datetime.utcnow()
    change.approved_by = current_user.id

    if not payload.approve:
        change.status = ProposedChangeStatusEnum.REJECTED
        change.rejection_reason = payload.reason
        db.add(change)
        db.commit()
        return {"status": "rejected", "change_id": change.id}

    if change.action_type == "MOVE_EVENT":
        event = _get_event_or_404(db, change.event_id)
        old_state = {
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat(),
            "room_id": event.room_id,
        }
        event.start_time = datetime.fromisoformat(change.payload["new_start_time"])
        event.end_time = datetime.fromisoformat(change.payload["new_end_time"])
        new_room_id = change.payload.get("new_room_id")
        if new_room_id:
            event.room_id = new_room_id
        event.status = EventStatusEnum.MOVED
        event.reason = change.payload.get("reason")

        _create_audit(
            db,
            action="APPROVE_MOVE_EVENT",
            user_id=current_user.id,
            event_id=event.id,
            old_value=old_state,
            new_value=change.payload,
            reason=payload.reason or change.payload.get("reason"),
        )
        _notify_group_users(
            db,
            group_id=event.group_id,
            title="Changement validé",
            message=f"Le changement pour le cours {event.course.name} a été validé.",
        )

    change.status = ProposedChangeStatusEnum.APPROVED
    db.add(change)
    db.commit()

    trigger_webhook(
        settings.N8N_EDITION_WEBHOOK_URL,
        {
            "intent": "APPROVED_CHANGE",
            "change_id": change.id,
            "approved_by": current_user.id,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )
    return {"status": "approved", "change_id": change.id}


__all__ = ["create_event", "cancel_event", "move_event", "approve_or_reject_change", "event_to_out"]
