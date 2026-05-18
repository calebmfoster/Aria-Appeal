"""add project created_at

Revision ID: b2f3a4c5d6e7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2f3a4c5d6e7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('project', sa.Column('created_at', sa.DateTime(timezone=True), nullable=True))
    # Backfill existing rows with current timestamp
    op.execute("UPDATE project SET created_at = NOW() WHERE created_at IS NULL")


def downgrade() -> None:
    op.drop_column('project', 'created_at')
