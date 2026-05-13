import enum

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class RoleEnum(str, enum.Enum):
    STUDENT = "STUDENT"
    STAFF = "STAFF"
    DIRECTOR = "DIRECTOR"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum), nullable=False)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("academic_groups.id"), nullable=True)

    group = relationship("AcademicGroup", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user")
    proposed_changes = relationship("ProposedChange", back_populates="requested_by_user", foreign_keys="ProposedChange.requested_by")
    approved_changes = relationship("ProposedChange", back_populates="approved_by_user", foreign_keys="ProposedChange.approved_by")
    notifications = relationship("Notification", back_populates="user")
