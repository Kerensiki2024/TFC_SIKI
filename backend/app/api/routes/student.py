from datetime import datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.event import Event, EventStatusEnum
from app.models.notification import Notification
from app.models.user import RoleEnum, User
from app.schemas.event import EventOut, NotificationOut
from app.services.student_service import event_to_out

router = APIRouter()


@router.get("/next-course", response_model=EventOut)
def next_course(
    current_user: User = Depends(require_roles(RoleEnum.STUDENT, RoleEnum.STAFF, RoleEnum.DIRECTOR)),
    db: Session = Depends(get_db),
    group_id: int | None = Query(default=None),
):
    target_group_id = group_id or current_user.group_id
    if not target_group_id:
        raise HTTPException(status_code=400, detail="group_id is required for this user")

    now = datetime.utcnow()
    stmt = (
        select(Event)
        .options(joinedload(Event.course), joinedload(Event.group), joinedload(Event.room))
        .where(
            Event.group_id == target_group_id,
            Event.start_time >= now,
            Event.status != EventStatusEnum.CANCELLED,
        )
        .order_by(Event.start_time.asc())
    )
    event = db.execute(stmt).scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="No upcoming course found")
    return event_to_out(event)


@router.get("/today", response_model=list[EventOut])
def today_planning(
    current_user: User = Depends(require_roles(RoleEnum.STUDENT, RoleEnum.STAFF, RoleEnum.DIRECTOR)),
    db: Session = Depends(get_db),
    group_id: int | None = Query(default=None),
):
    target_group_id = group_id or current_user.group_id
    if not target_group_id:
        raise HTTPException(status_code=400, detail="group_id is required for this user")

    now = datetime.utcnow()
    start_of_day = datetime.combine(now.date(), time.min)
    end_of_day = datetime.combine(now.date(), time.max)

    stmt = (
        select(Event)
        .options(joinedload(Event.course), joinedload(Event.group), joinedload(Event.room))
        .where(
            Event.group_id == target_group_id,
            and_(Event.start_time >= start_of_day, Event.start_time <= end_of_day),
        )
        .order_by(Event.start_time.asc())
    )
    return [event_to_out(item) for item in db.execute(stmt).scalars().all()]


@router.get("/week", response_model=list[EventOut])
def week_planning(
    current_user: User = Depends(require_roles(RoleEnum.STUDENT, RoleEnum.STAFF, RoleEnum.DIRECTOR)),
    db: Session = Depends(get_db),
    group_id: int | None = Query(default=None),
):
    target_group_id = group_id or current_user.group_id
    if not target_group_id:
        raise HTTPException(status_code=400, detail="group_id is required for this user")

    now = datetime.utcnow()
    start = datetime.combine(now.date(), time.min)
    end = start + timedelta(days=7)

    stmt = (
        select(Event)
        .options(joinedload(Event.course), joinedload(Event.group), joinedload(Event.room))
        .where(
            Event.group_id == target_group_id,
            and_(Event.start_time >= start, Event.start_time < end),
        )
        .order_by(Event.start_time.asc())
    )
    return [event_to_out(item) for item in db.execute(stmt).scalars().all()]


@router.get("/notifications", response_model=list[NotificationOut])
def my_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
    )
    return db.execute(stmt).scalars().all()
