import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class EventTypeEnum(str, enum.Enum):
    COURS = "COURS"
    TP = "TP"
    EXAMEN = "EXAMEN"


class EventStatusEnum(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    CANCELLED = "CANCELLED"
    MOVED = "MOVED"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    type: Mapped[EventTypeEnum] = mapped_column(Enum(EventTypeEnum), nullable=False)
    status: Mapped[EventStatusEnum] = mapped_column(Enum(EventStatusEnum), default=EventStatusEnum.SCHEDULED, nullable=False)
    teacher_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    group_id: Mapped[int] = mapped_column(ForeignKey("academic_groups.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), nullable=False)

    group = relationship("AcademicGroup", back_populates="events")
    course = relationship("Course", back_populates="events")
    room = relationship("Room", back_populates="events")
    audit_logs = relationship("AuditLog", back_populates="event")
    proposed_changes = relationship("ProposedChange", back_populates="event")
