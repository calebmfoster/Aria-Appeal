"""add videoclip and project video fields

Revision ID: d76bdbc65413
Revises: d4e5f6a7b8c9
Create Date: 2026-06-28 12:09:24.278436

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd76bdbc65413'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "videoclip",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("segment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column(
            "source_type",
            sa.Enum("GENERATED", "ASSET", "UPLOADED", name="videosourcetype"),
            nullable=False,
        ),
        sa.Column("prompt", sa.String(), nullable=True),
        sa.Column("video_url", sa.String(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("PENDING", "GENERATING", "READY", "FAILED", name="videoclipstatus"),
            nullable=False,
        ),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("trim_start_ms", sa.Integer(), nullable=True),
        sa.Column("trim_end_ms", sa.Integer(), nullable=True),
        sa.Column("timeline_start_ms", sa.Integer(), nullable=True),
        sa.Column("timeline_end_ms", sa.Integer(), nullable=True),
        sa.Column("init_image_path", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.ForeignKeyConstraint(["segment_id"], ["scriptsegment.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column("project", sa.Column("video_brief", sa.JSON(), nullable=True))
    op.add_column("project", sa.Column("subtitle_style", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("project", "subtitle_style")
    op.drop_column("project", "video_brief")
    op.drop_table("videoclip")
    sa.Enum(name="videoclipstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="videosourcetype").drop(op.get_bind(), checkfirst=True)
