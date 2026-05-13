from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class AcademicGroup(Base):
    __tablename__ = "academic_groups"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    level: Mapped[str] = mapped_column(String(50), nullable=False)
    filiere: Mapped[str] = mapped_column(String(100), nullable=False)

    users = relationship("User", back_populates="group")
    events = relationship("Event", back_populates="group")
