"""remove_pending_status

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-06-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE reservations SET status = 'CONFIRMED' WHERE status = 'PENDING'")
    op.drop_constraint('ck_reservations_status', 'reservations', type_='check')
    op.create_check_constraint(
        'ck_reservations_status',
        'reservations',
        "status IN ('CONFIRMED', 'CANCELLED')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_reservations_status', 'reservations', type_='check')
    op.create_check_constraint(
        'ck_reservations_status',
        'reservations',
        "status IN ('PENDING', 'CONFIRMED', 'CANCELLED')",
    )
