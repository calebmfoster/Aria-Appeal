"""Add speaker_preset and pitch_shift to scriptsegment

Revision ID: d4e5f6a7b8c9
Revises: b2f3a4c5d6e7
Create Date: 2026-05-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'b2f3a4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('scriptsegment', sa.Column('speaker_preset', sa.String(), nullable=True))
    op.add_column('scriptsegment', sa.Column('pitch_shift', sa.Float(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('scriptsegment', 'pitch_shift')
    op.drop_column('scriptsegment', 'speaker_preset')
