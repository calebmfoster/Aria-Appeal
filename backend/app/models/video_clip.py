from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional
import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, Integer, Enum, DateTime
from app.db.base_class import Base

if TYPE_CHECKING:
    from .project import Project
    from .script_segment import ScriptSegment


class VideoSourceType(str, enum.Enum):
    GENERATED = "generated"
    ASSET = "asset"
    UPLOADED = "uploaded"


class VideoClipStatus(str, enum.Enum):
    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class VideoClip(Base):
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("project.id"))
    segment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("scriptsegment.id"), nullable=True
    )
    sequence_order: Mapped[int] = mapped_column(Integer)
    source_type: Mapped[VideoSourceType] = mapped_column(
        Enum(VideoSourceType), default=VideoSourceType.GENERATED
    )
    prompt: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[VideoClipStatus] = mapped_column(
        Enum(VideoClipStatus), default=VideoClipStatus.PENDING
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    trim_start_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    trim_end_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    timeline_start_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    timeline_end_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    init_image_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    project: Mapped["Project"] = relationship("Project", back_populates="video_clips")
