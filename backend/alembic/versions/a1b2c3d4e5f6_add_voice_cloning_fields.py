"""Add voice cloning reference fields

Revision ID: a1b2c3d4e5f6
Revises: 99a81756ea78
Create Date: 2026-03-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '99a81756ea78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add reference_audio_path and reference_text to voiceprofile."""
    op.add_column('voiceprofile', sa.Column('reference_audio_path', sa.String(), nullable=True))
    op.add_column('voiceprofile', sa.Column('reference_text', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove reference_audio_path and reference_text from voiceprofile."""
    op.drop_column('voiceprofile', 'reference_text')
    op.drop_column('voiceprofile', 'reference_audio_path')
