from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional, TYPE_CHECKING
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, JSON, Enum, DateTime
from app.db.base_class import Base
import enum

if TYPE_CHECKING:
    from .user import User
    from .script_segment import ScriptSegment

class ProjectStatus(str, enum.Enum):
    DRAFT = "draft"
    GENERATED = "generated"
    MASTERED = "mastered"

class Project(Base):
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"))
    title: Mapped[str] = mapped_column(String, index=True)
    target_audience: Mapped[dict] = mapped_column(JSON)
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.DRAFT)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    owner: Mapped["User"] = relationship("User", back_populates="projects")
    segments: Mapped[List["ScriptSegment"]] = relationship("ScriptSegment", back_populates="project")
