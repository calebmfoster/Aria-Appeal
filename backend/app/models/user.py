from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, TYPE_CHECKING
import uuid
from sqlalchemy import String, DateTime, func
from app.db.base_class import Base

if TYPE_CHECKING:
    from .project import Project
    from .voice_profile import VoiceProfile

class User(Base):
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    projects: Mapped[List["Project"]] = relationship("Project", back_populates="owner")
    voice_profiles: Mapped[List["VoiceProfile"]] = relationship("VoiceProfile", back_populates="owner")
