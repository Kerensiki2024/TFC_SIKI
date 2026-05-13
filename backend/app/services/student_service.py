from app.schemas.event import EventOut


def event_to_out(event) -> EventOut:
    return EventOut(
        id=event.id,
        course=event.course.name,
        group=event.group.name,
        room=event.room.name,
        teacher_name=event.teacher_name,
        type=event.type.value,
        status=event.status.value,
        start_time=event.start_time,
        end_time=event.end_time,
    )
