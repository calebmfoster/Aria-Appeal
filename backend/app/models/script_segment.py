from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional
import uuid
from sqlalchemy import String, ForeignKey, Integer, Float
from app.db.base_class import Base

if TYPE_CHECKING:
    from .project import Project

class ScriptSegment(Base):
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("project.id"))
    text: Mapped[str] = mapped_column(String)
    start_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    audio_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    emotion: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    voice_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("voiceprofile.id"), nullable=True)
    speaker_preset: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    pitch_shift: Mapped[float] = mapped_column(Float, default=0.0)
    sequence_order: Mapped[int] = mapped_column(Integer)

    project: Mapped["Project"] = relationship("Project", back_populates="segments")
