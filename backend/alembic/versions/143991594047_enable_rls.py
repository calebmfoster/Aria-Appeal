"""enable_rls

Revision ID: 143991594047
Revises: 3c7377c3e9a2
Create Date: 2026-02-25 16:03:45.178280

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '143991594047'
down_revision: Union[str, Sequence[str], None] = '3c7377c3e9a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute('ALTER TABLE "user" ENABLE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE "project" ENABLE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE "scriptsegment" ENABLE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE "voiceprofile" ENABLE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE "alembic_version" ENABLE ROW LEVEL SECURITY;')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('ALTER TABLE "alembic_version" DISABLE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE "voiceprofile" DISABLE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE "scriptsegment" DISABLE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE "project" DISABLE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE "user" DISABLE ROW LEVEL SECURITY;')
