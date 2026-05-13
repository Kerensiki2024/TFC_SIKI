from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.course import Course
from app.models.event import Event, EventStatusEnum, EventTypeEnum
from app.models.group import AcademicGroup
from app.models.room import Room
from app.models.user import RoleEnum, User


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        has_user = db.execute(select(User)).scalars().first()
        if has_user:
            print("Seed skipped: data already exists")
            return

        group1 = AcademicGroup(name="L1-INFO-A", level="L1", filiere="Informatique")
        group2 = AcademicGroup(name="L2-MATH-A", level="L2", filiere="Mathématiques")
        db.add_all([group1, group2])
        db.flush()

        room1 = Room(name="C3", building="Bloc C")
        room2 = Room(name="B2", building="Bloc B")
        room3 = Room(name="E15", building="Bloc E")
        db.add_all([room1, room2, room3])
        db.flush()

        course1 = Course(code="PROG1", name="Programmation 1")
        course2 = Course(code="RESX", name="Réseaux")
        course3 = Course(code="MATHX", name="Maths")
        db.add_all([course1, course2, course3])
        db.flush()

        student = User(
            email="alice@student.local",
            full_name="Alice Student",
            password_hash=hash_password("password123"),
            role=RoleEnum.STUDENT,
            group_id=group1.id,
        )
        staff = User(
            email="bob.staff@polytech.local",
            full_name="Bob Staff",
            password_hash=hash_password("password123"),
            role=RoleEnum.STAFF,
        )
        director = User(
            email="director@polytech.local",
            full_name="Directeur Académique",
            password_hash=hash_password("password123"),
            role=RoleEnum.DIRECTOR,
        )
        db.add_all([student, staff, director])
        db.flush()

        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        events = [
            Event(
                start_time=now + timedelta(hours=2),
                end_time=now + timedelta(hours=4),
                type=EventTypeEnum.COURS,
                status=EventStatusEnum.SCHEDULED,
                teacher_name="Prof. Martin",
                group_id=group1.id,
                course_id=course1.id,
                room_id=room1.id,
            ),
            Event(
                start_time=now + timedelta(days=1, hours=8),
                end_time=now + timedelta(days=1, hours=10),
                type=EventTypeEnum.COURS,
                status=EventStatusEnum.SCHEDULED,
                teacher_name="Prof. Nsimba",
                group_id=group1.id,
                course_id=course2.id,
                room_id=room2.id,
            ),
            Event(
                start_time=now + timedelta(days=3, hours=9),
                end_time=now + timedelta(days=3, hours=11),
                type=EventTypeEnum.EXAMEN,
                status=EventStatusEnum.SCHEDULED,
                teacher_name="Prof. Kanku",
                group_id=group2.id,
                course_id=course3.id,
                room_id=room3.id,
            ),
        ]
        db.add_all(events)
        db.commit()
        print("Seed completed")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
