from datetime import datetime

from pydantic import BaseModel


class EventOut(BaseModel):
    id: int
    course: str
    group: str
    room: str
    teacher_name: str | None = None
    type: str
    status: str
    start_time: datetime
    end_time: datetime

    class Config:
        from_attributes = True


class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    channel: str
    is_read: bool
    created_at: datetime
