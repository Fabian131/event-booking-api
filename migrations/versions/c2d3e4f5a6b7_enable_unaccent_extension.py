"""enable_unaccent_extension

Revision ID: c2d3e4f5a6b7
Revises: b7c8d9e0f1a2
Create Date: 2026-06-12 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS unaccent')


def downgrade() -> None:
    op.execute('DROP EXTENSION IF EXISTS unaccent')
