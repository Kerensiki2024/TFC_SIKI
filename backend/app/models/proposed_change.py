import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class ProposedChangeStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ProposedChange(Base):
    __tablename__ = "proposed_changes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[ProposedChangeStatusEnum] = mapped_column(Enum(ProposedChangeStatusEnum), default=ProposedChangeStatusEnum.PENDING, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"), nullable=True)
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    event = relationship("Event", back_populates="proposed_changes")
    requested_by_user = relationship("User", foreign_keys=[requested_by], back_populates="proposed_changes")
    approved_by_user = relationship("User", foreign_keys=[approved_by], back_populates="approved_changes")
