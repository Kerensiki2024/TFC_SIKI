"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-04-19 00:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'academic_groups',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False, unique=True),
        sa.Column('level', sa.String(length=50), nullable=False),
        sa.Column('filiere', sa.String(length=100), nullable=False),
    )
    op.create_index(op.f('ix_academic_groups_id'), 'academic_groups', ['id'], unique=False)

    op.create_table(
        'courses',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('code', sa.String(length=50), nullable=False, unique=True),
        sa.Column('name', sa.String(length=150), nullable=False),
    )
    op.create_index(op.f('ix_courses_id'), 'courses', ['id'], unique=False)

    op.create_table(
        'rooms',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=50), nullable=False, unique=True),
        sa.Column('building', sa.String(length=100), nullable=True),
    )
    op.create_index(op.f('ix_rooms_id'), 'rooms', ['id'], unique=False)

    role_enum = sa.Enum('STUDENT', 'STAFF', 'DIRECTOR', name='roleenum')
    role_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(length=150), nullable=False, unique=True),
        sa.Column('full_name', sa.String(length=150), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', role_enum, nullable=False),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('academic_groups.id'), nullable=True),
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    event_type_enum = sa.Enum('COURS', 'TP', 'EXAMEN', name='eventtypeenum')
    event_status_enum = sa.Enum('SCHEDULED', 'CANCELLED', 'MOVED', name='eventstatusenum')
    event_type_enum.create(op.get_bind(), checkfirst=True)
    event_status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        'events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('type', event_type_enum, nullable=False),
        sa.Column('status', event_status_enum, nullable=False),
        sa.Column('teacher_name', sa.String(length=150), nullable=True),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('academic_groups.id'), nullable=False),
        sa.Column('course_id', sa.Integer(), sa.ForeignKey('courses.id'), nullable=False),
        sa.Column('room_id', sa.Integer(), sa.ForeignKey('rooms.id'), nullable=False),
    )
    op.create_index(op.f('ix_events_id'), 'events', ['id'], unique=False)

    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('channel', sa.String(length=50), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)

    proposed_enum = sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='proposedchangestatusenum')
    proposed_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        'proposed_changes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('is_sensitive', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('status', proposed_enum, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('decided_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.String(length=255), nullable=True),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('events.id'), nullable=True),
        sa.Column('requested_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('approved_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
    )
    op.create_index(op.f('ix_proposed_changes_id'), 'proposed_changes', ['id'], unique=False)

    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('old_value', sa.JSON(), nullable=True),
        sa.Column('new_value', sa.JSON(), nullable=True),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('events.id'), nullable=True),
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_logs_id'), table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_index(op.f('ix_proposed_changes_id'), table_name='proposed_changes')
    op.drop_table('proposed_changes')
    op.drop_index(op.f('ix_notifications_id'), table_name='notifications')
    op.drop_table('notifications')
    op.drop_index(op.f('ix_events_id'), table_name='events')
    op.drop_table('events')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_rooms_id'), table_name='rooms')
    op.drop_table('rooms')
    op.drop_index(op.f('ix_courses_id'), table_name='courses')
    op.drop_table('courses')
    op.drop_index(op.f('ix_academic_groups_id'), table_name='academic_groups')
    op.drop_table('academic_groups')
