"""merge_schedule_into_event

Revision ID: a1b2c3d4e5f6
Revises: 061dcaaf79fa
Create Date: 2026-06-05 04:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '061dcaaf79fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add role to users
    op.add_column('users', sa.Column('role', sa.String(length=20), nullable=False, server_default='customer'))

    # 2. Add schedule fields + image_url to events
    op.add_column('events', sa.Column('date', sa.Date(), nullable=True))
    op.add_column('events', sa.Column('start_time', sa.Time(), nullable=True))
    op.add_column('events', sa.Column('end_time', sa.Time(), nullable=True))
    op.add_column('events', sa.Column('image_url', sa.String(length=500), nullable=True))

    # 3. Migrate data from event_schedules to events (copy first schedule per event)
    op.execute("""
        UPDATE events e
        SET date = es.schedule_date,
            start_time = es.start_time,
            end_time = es.end_time
        FROM (
            SELECT DISTINCT ON (event_id) event_id, schedule_date, start_time, end_time
            FROM event_schedules
            ORDER BY event_id, schedule_date ASC
        ) es
        WHERE e.id = es.event_id
    """)

    # 4. Set defaults for events without schedules
    op.execute("""
        UPDATE events
        SET date = CURRENT_DATE,
            start_time = '09:00:00',
            end_time = '17:00:00'
        WHERE date IS NULL
    """)

    # 5. Make date/time columns NOT NULL
    op.alter_column('events', 'date', nullable=False)
    op.alter_column('events', 'start_time', nullable=False)
    op.alter_column('events', 'end_time', nullable=False)

    # 6. Change title max length from 150 to 64
    op.alter_column('events', 'title', type_=sa.String(length=64), existing_type=sa.String(length=150))

    # 7. Add time range check constraint
    op.create_check_constraint('ck_events_time_range', 'events', 'end_time > start_time')

    # 8. Drop location column from events
    op.drop_column('events', 'location')

    # 9. Add event_id to reservations (initially nullable for migration)
    op.add_column('reservations', sa.Column('event_id', sa.UUID(), nullable=True))

    # 10. Migrate reservation data: map event_schedule_id -> event_id
    op.execute("""
        UPDATE reservations r
        SET event_id = es.event_id
        FROM event_schedules es
        WHERE r.event_schedule_id = es.id
    """)

    # 11. Make event_id NOT NULL
    op.alter_column('reservations', 'event_id', nullable=False)

    # 12. Add FK for event_id
    op.create_foreign_key('fk_reservations_event_id', 'reservations', 'events', ['event_id'], ['id'], ondelete='RESTRICT')

    # 13. Rename quantity -> ticket_quantity
    op.alter_column('reservations', 'quantity', new_column_name='ticket_quantity')

    # 14. Update check constraint for new column name
    op.drop_constraint('ck_reservations_quantity', 'reservations', type_='check')
    op.create_check_constraint('ck_reservations_ticket_quantity', 'reservations', 'ticket_quantity > 0')

    # 15. Drop old FK and column event_schedule_id
    op.drop_constraint('reservations_event_schedule_id_fkey', 'reservations', type_='foreignkey')
    op.drop_column('reservations', 'event_schedule_id')

    # 16. Add event_id to notifications
    op.add_column('notifications', sa.Column('event_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_notifications_event_id', 'notifications', 'events', ['event_id'], ['id'], ondelete='SET NULL')

    # 17. Drop event_schedules table
    op.drop_table('event_schedules')


def downgrade() -> None:
    # Recreate event_schedules table
    op.create_table('event_schedules',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('event_id', sa.UUID(), nullable=False),
        sa.Column('schedule_date', sa.Date(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('available_slots', sa.SmallInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('available_slots >= 0', name='ck_event_schedules_available_slots'),
        sa.CheckConstraint('end_time > start_time', name='ck_event_schedules_time_range'),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Remove event_id from notifications
    op.drop_constraint('fk_notifications_event_id', 'notifications', type_='foreignkey')
    op.drop_column('notifications', 'event_id')

    # Restore event_schedule_id on reservations
    op.add_column('reservations', sa.Column('event_schedule_id', sa.UUID(), nullable=True))
    op.drop_constraint('ck_reservations_ticket_quantity', 'reservations', type_='check')
    op.alter_column('reservations', 'ticket_quantity', new_column_name='quantity')
    op.create_check_constraint('ck_reservations_quantity', 'reservations', 'quantity > 0')
    op.drop_constraint('fk_reservations_event_id', 'reservations', type_='foreignkey')
    op.drop_column('reservations', 'event_id')

    # Restore events columns
    op.add_column('events', sa.Column('location', sa.String(length=100), nullable=True))
    op.drop_constraint('ck_events_time_range', 'events', type_='check')
    op.alter_column('events', 'title', type_=sa.String(length=150), existing_type=sa.String(length=64))
    op.drop_column('events', 'image_url')
    op.drop_column('events', 'end_time')
    op.drop_column('events', 'start_time')
    op.drop_column('events', 'date')

    # Remove role from users
    op.drop_column('users', 'role')
