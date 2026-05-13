from datetime import datetime

from pydantic import BaseModel


class EventCreateRequest(BaseModel):
    course_id: int
    group_id: int
    room_id: int
    teacher_name: str | None = None
    type: str = "COURS"
    start_time: datetime
    end_time: datetime


class CancelEventRequest(BaseModel):
    reason: str = "Annulé par l'administration"


class MoveEventRequest(BaseModel):
    new_start_time: datetime
    new_end_time: datetime
    new_room_id: int | None = None
    reason: str = "Cours déplacé"


class DecisionRequest(BaseModel):
    approve: bool
    reason: str | None = None


class ProposedChangeOut(BaseModel):
    id: int
    action_type: str
    payload: dict
    is_sensitive: bool
    status: str
    created_at: datetime
